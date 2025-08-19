from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import StreamingResponse, Response
import sqlite3
import json
import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes
import os
from typing import Optional, List
from .main import Database, require_auth, require_role, log_audit, UPLOADS_DIR

router = APIRouter()

@router.get("/api/events/{event_id}/schedules")
async def get_event_schedules(event_id: int, user = Depends(require_auth)):
    schedules = Database.execute_query(
        "SELECT * FROM schedules WHERE event_id = ? ORDER BY start_at",
        (event_id,),
        fetch_all=True
    )
    
    return [dict(schedule) for schedule in schedules]

@router.post("/api/events/{event_id}/schedules")
async def create_schedule(event_id: int, request: Request, user = Depends(require_role(["admin", "teacher"]))):
    data = await request.json()
    
    required_fields = ["title", "venue", "start_at", "end_at"]
    for field in required_fields:
        if not data.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required")
    
    schedule_id = Database.execute_query(
        "INSERT INTO schedules (event_id, title, venue, start_at, end_at, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (event_id, data["title"], data["venue"], data["start_at"], data["end_at"], data.get("notes", ""))
    )
    
    log_audit(user["id"], "create", "schedule", schedule_id)
    
    return {"id": schedule_id, "message": "Schedule created"}

@router.get("/api/events/{event_id}/logistics")
async def get_event_logistics(event_id: int, user = Depends(require_auth)):
    logistics = Database.execute_query(
        "SELECT * FROM logistics WHERE event_id = ? ORDER BY created_at",
        (event_id,),
        fetch_all=True
    )
    
    result = []
    for item in logistics:
        item_dict = dict(item)
        item_dict["details"] = json.loads(item_dict["details_json"])
        del item_dict["details_json"]
        result.append(item_dict)
    
    return result

@router.post("/api/events/{event_id}/logistics")
async def create_logistics(event_id: int, request: Request, user = Depends(require_role(["admin", "teacher"]))):
    data = await request.json()
    
    if not data.get("type") or not data.get("details"):
        raise HTTPException(status_code=400, detail="Type and details are required")
    
    logistics_id = Database.execute_query(
        "INSERT INTO logistics (event_id, type, details_json) VALUES (?, ?, ?)",
        (event_id, data["type"], json.dumps(data["details"]))
    )
    
    log_audit(user["id"], "create", "logistics", logistics_id)
    
    return {"id": logistics_id, "message": "Logistics created"}

@router.get("/api/events/{event_id}/tasks")
async def get_event_tasks(event_id: int, user = Depends(require_auth)):
    tasks = Database.execute_query(
        """SELECT t.*, u.name as assignee_name 
           FROM tasks t 
           LEFT JOIN users u ON t.assignee_user_id = u.id 
           WHERE t.event_id = ? ORDER BY t.due_at""",
        (event_id,),
        fetch_all=True
    )
    
    return [dict(task) for task in tasks]

@router.post("/api/events/{event_id}/tasks")
async def create_task(event_id: int, request: Request, user = Depends(require_role(["admin", "teacher"]))):
    data = await request.json()
    
    if not data.get("title"):
        raise HTTPException(status_code=400, detail="Title is required")
    
    task_id = Database.execute_query(
        "INSERT INTO tasks (event_id, title, assignee_user_id, status, due_at, description) VALUES (?, ?, ?, ?, ?, ?)",
        (event_id, data["title"], data.get("assignee_user_id"), 
         data.get("status", "pending"), data.get("due_at"), data.get("description", ""))
    )
    
    log_audit(user["id"], "create", "task", task_id)
    
    return {"id": task_id, "message": "Task created"}

@router.put("/api/tasks/{task_id}")
async def update_task(task_id: int, request: Request, user = Depends(require_auth)):
    data = await request.json()
    
    task = Database.execute_query(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,),
        fetch_one=True
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_fields = []
    params = []
    
    for field in ["title", "assignee_user_id", "status", "due_at", "description"]:
        if field in data:
            update_fields.append(f"{field} = ?")
            params.append(data[field])
    
    if update_fields:
        params.append(task_id)
        Database.execute_query(
            f"UPDATE tasks SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            tuple(params)
        )
        
        log_audit(user["id"], "update", "task", task_id, data)
    
    return {"message": "Task updated"}

@router.get("/api/events/{event_id}/announcements")
async def get_event_announcements(event_id: int, user = Depends(require_auth)):
    announcements = Database.execute_query(
        """SELECT a.*, u.name as author_name 
           FROM announcements a 
           JOIN users u ON a.created_by = u.id 
           WHERE a.event_id = ? OR a.event_id IS NULL 
           ORDER BY a.created_at DESC""",
        (event_id,),
        fetch_all=True
    )
    
    return [dict(announcement) for announcement in announcements]

@router.post("/api/events/{event_id}/announcements")
async def create_announcement(event_id: int, request: Request, user = Depends(require_role(["admin", "teacher"]))):
    data = await request.json()
    
    if not data.get("title") or not data.get("body"):
        raise HTTPException(status_code=400, detail="Title and body are required")
    
    announcement_id = Database.execute_query(
        "INSERT INTO announcements (event_id, title, body, created_by) VALUES (?, ?, ?, ?)",
        (event_id, data["title"], data["body"], user["id"])
    )
    
    log_audit(user["id"], "create", "announcement", announcement_id)
    
    return {"id": announcement_id, "message": "Announcement created"}

@router.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    event_id: Optional[int] = None,
    owner_type: str = "event",
    owner_id: int = 0,
    user = Depends(require_auth)
):
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    allowed_types = ["image/jpeg", "image/png", "image/gif", "application/pdf", "text/csv", "application/vnd.ms-excel"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    file_ext = Path(file.filename).suffix
    safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = UPLOADS_DIR / safe_filename
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    file_id = Database.execute_query(
        "INSERT INTO files (event_id, owner_type, owner_id, filename, mime, size, path, uploaded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (event_id, owner_type, owner_id, file.filename, file.content_type, file.size, str(file_path), user["id"])
    )
    
    log_audit(user["id"], "upload", "file", file_id)
    
    return {"id": file_id, "filename": file.filename, "message": "File uploaded"}

@router.get("/api/files/{file_id}")
async def download_file(file_id: int, user = Depends(require_auth)):
    file_record = Database.execute_query(
        "SELECT * FROM files WHERE id = ?",
        (file_id,),
        fetch_one=True
    )
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = Path(file_record["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return StreamingResponse(
        io.BytesIO(file_path.read_bytes()),
        media_type=file_record["mime"],
        headers={"Content-Disposition": f"attachment; filename={file_record['filename']}"}
    )

@router.get("/api/reports/participants/csv")
async def export_participants_csv(user = Depends(require_auth)):
    participants = Database.execute_query(
        "SELECT * FROM participants ORDER BY last_name, first_name",
        fetch_all=True
    )
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["ID", "First Name", "Last Name", "Grade", "Section", "Email", "Phone", "Guardian Name", "Guardian Phone", "Medical Notes"])
    
    for p in participants:
        writer.writerow([
            p["id"], p["first_name"], p["last_name"], p["grade"], p["section"],
            p["email"], p["phone"], p["guardian_name"], p["guardian_phone"], p["medical_notes"]
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=participants.csv"}
    )

@router.get("/api/reports/events/csv")
async def export_events_csv(user = Depends(require_auth)):
    events = Database.execute_query(
        "SELECT * FROM events ORDER BY start_at DESC",
        fetch_all=True
    )
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["ID", "Title", "Host", "Location", "Start Date", "End Date", "Category", "Status", "Description"])
    
    for e in events:
        writer.writerow([
            e["id"], e["title"], e["host"], e["location"], e["start_at"], 
            e["end_at"], e["category"], e["status"], e["description"]
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=events.csv"}
    )

@router.get("/api/schedules/{participant_id}/ics")
async def export_participant_schedule_ics(participant_id: int, user = Depends(require_auth)):
    schedules = Database.execute_query(
        """SELECT s.*, e.title as event_title 
           FROM schedules s 
           JOIN events e ON s.event_id = e.id 
           JOIN teams t ON t.event_id = e.id 
           JOIN team_members tm ON tm.team_id = t.id 
           WHERE tm.participant_id = ? 
           ORDER BY s.start_at""",
        (participant_id,),
        fetch_all=True
    )
    
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Arista//Event Schedule//EN\n"
    
    for schedule in schedules:
        start_dt = datetime.fromisoformat(schedule["start_at"]).strftime("%Y%m%dT%H%M%S")
        end_dt = datetime.fromisoformat(schedule["end_at"]).strftime("%Y%m%dT%H%M%S")
        
        ics_content += f"BEGIN:VEVENT\n"
        ics_content += f"UID:{schedule['id']}@arista.school\n"
        ics_content += f"DTSTART:{start_dt}\n"
        ics_content += f"DTEND:{end_dt}\n"
        ics_content += f"SUMMARY:{schedule['title']} - {schedule['event_title']}\n"
        ics_content += f"LOCATION:{schedule['venue']}\n"
        if schedule["notes"]:
            ics_content += f"DESCRIPTION:{schedule['notes']}\n"
        ics_content += f"END:VEVENT\n"
    
    ics_content += "END:VCALENDAR\n"
    
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=schedule.ics"}
    )

@router.get("/api/audit")
async def get_audit_log(
    page: int = 1,
    limit: int = 50,
    user = Depends(require_role(["admin"]))
):
    offset = (page - 1) * limit
    
    logs = Database.execute_query(
        """SELECT a.*, u.name as user_name 
           FROM audit_log a 
           JOIN users u ON a.user_id = u.id 
           ORDER BY a.created_at DESC 
           LIMIT ? OFFSET ?""",
        (limit, offset),
        fetch_all=True
    )
    
    total = Database.execute_query(
        "SELECT COUNT(*) as count FROM audit_log",
        fetch_one=True
    )
    
    return {
        "logs": [dict(log) for log in logs],
        "total": total["count"],
        "page": page,
        "pages": (total["count"] + limit - 1) // limit
    }
