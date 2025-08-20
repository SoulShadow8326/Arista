from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import json
from pathlib import Path
import secrets
import sqlite3
import bcrypt
import string
from datetime import datetime, timedelta
from jose import jwt, JWTError

import os

SECRET_KEY = os.environ.get('ARISTA_SECRET_KEY', "arista-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

def create_access_token(data: dict):
    to_encode = data.copy()
    if 'sub' in to_encode:
        to_encode['sub'] = str(to_encode['sub'])
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

DB_PATH = Path(__file__).parent.parent / "arista.db"
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

class Database:
    _initialized = False
    
    @classmethod
    def initialize(cls):
        if cls._initialized:
            return
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    admin_email TEXT NOT NULL,
                    address TEXT,
                    phone TEXT,
                    website TEXT,
                    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    school_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student', 'student_coordinator')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (school_id) REFERENCES schools (id) ON DELETE CASCADE,
                    UNIQUE(school_id, email)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    school_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    start_at TIMESTAMP NOT NULL,
                    end_at TIMESTAMP NOT NULL,
                    location TEXT,
                    host TEXT,
                    notes TEXT,
                    registration_link TEXT,
                    max_participants INTEGER,
                    status TEXT DEFAULT 'upcoming' CHECK (status IN ('upcoming', 'ongoing', 'completed', 'cancelled')),
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (school_id) REFERENCES schools (id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'registered' CHECK (status IN ('registered', 'waitlisted', 'cancelled')),
                    attendance_status TEXT DEFAULT 'absent' CHECK (attendance_status IN ('present', 'absent', 'late')),
                    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE(event_id, user_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE(event_id, name)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS team_members (
                    team_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    role TEXT DEFAULT 'member' CHECK (role IN ('leader', 'member')),
                    PRIMARY KEY (team_id, user_id),
                    FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id INTEGER,
                    meta_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    school_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (school_id) REFERENCES schools (id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            cursor.execute("PRAGMA table_info(announcements)")
            ann_cols = [r[1] for r in cursor.fetchall()]
            if 'event_id' not in ann_cols:
                try:
                    cursor.execute('ALTER TABLE announcements ADD COLUMN event_id INTEGER')
                except Exception:
                    pass
            cursor.execute("PRAGMA table_info(announcements)")
            ann_cols = [r[1] for r in cursor.fetchall()]
            if 'body' not in ann_cols and 'content' in ann_cols:
                try:
                    cursor.execute('ALTER TABLE announcements ADD COLUMN body TEXT')
                    cursor.execute("UPDATE announcements SET body = content WHERE body IS NULL AND content IS NOT NULL")
                except Exception:
                    pass

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    school_id INTEGER,
                    event_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','completed','cancelled')),
                    due_at TIMESTAMP,
                    due_date TIMESTAMP,
                    priority TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            cursor.execute("PRAGMA table_info(participants)")
            cols = [r[1] for r in cursor.fetchall()]
            if 'school_id' not in cols:
                try:
                    cursor.execute('ALTER TABLE participants ADD COLUMN school_id INTEGER')
                except Exception:
                    pass

            cursor.execute("PRAGMA table_info(events)")
            ev_cols = [r[1] for r in cursor.fetchall()]
            if 'title' not in ev_cols:
                try:
                    cursor.execute('ALTER TABLE events ADD COLUMN title TEXT')
                    if 'name' in ev_cols:
                        cursor.execute("UPDATE events SET title = name WHERE title IS NULL AND name IS NOT NULL")
                except Exception:
                    pass

            if 'start_at' not in ev_cols:
                try:
                    cursor.execute('ALTER TABLE events ADD COLUMN start_at TIMESTAMP')
                    if 'start_time' in ev_cols:
                        cursor.execute("UPDATE events SET start_at = start_time WHERE start_at IS NULL AND start_time IS NOT NULL")
                except Exception:
                    pass

            if 'end_at' not in ev_cols:
                try:
                    cursor.execute('ALTER TABLE events ADD COLUMN end_at TIMESTAMP')
                    if 'end_time' in ev_cols:
                        cursor.execute("UPDATE events SET end_at = end_time WHERE end_at IS NULL AND end_time IS NOT NULL")
                except Exception:
                    pass

            for col_name in ('host', 'notes', 'registration_link'):
                if col_name not in ev_cols:
                    try:
                        cursor.execute(f'ALTER TABLE events ADD COLUMN {col_name} TEXT')
                    except Exception:
                        pass
            
            conn.commit()
            cls._initialized = True
            print("Database tables created successfully")
        except Exception as e:
            conn.rollback()
            print(f"Error initializing database: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_connection():
        if not Database._initialized:
            Database.initialize()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
        if not Database._initialized:
            Database.initialize()
            
        conn = Database.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            
            if fetch_one:
                result = cursor.fetchone()
                if result is None:
                    return None
                return dict(result)
            elif fetch_all:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            print(f"Database error in execute_query: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()

app = FastAPI(title="Arista Event Planning Portal")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "html"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=json.loads(os.environ.get('ARISTA_CORS_ALLOW_ORIGINS', '["http://localhost:8000", "http://127.0.0.1:8000"]')),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

security = HTTPBearer(auto_error=False)

Database.initialize()

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return str(user_id) 
    except JWTError:
        return None

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = None
) -> Optional[dict]:
    token = None
    
    if hasattr(request.state, 'auth_token'):
        token = request.state.auth_token
    elif credentials and hasattr(credentials, 'credentials'):
        token = credentials.credentials
    
    if not token and 'access_token' in request.cookies:
        auth_cookie = request.cookies.get('access_token')
        if auth_cookie and auth_cookie.startswith('Bearer '):
            token = auth_cookie.split(' ')[1]
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
            
        user = Database.execute_query(
            """
            SELECT u.*, s.name as school_name, s.code as school_code 
            FROM users u 
            JOIN schools s ON u.school_id = s.id 
            WHERE u.id = ?
            """, 
            (user_id,), 
            fetch_one=True
        )
        
        if not user:
            return None
            
        user_dict = dict(user)
        user_dict["token"] = token
        return user_dict
        
    except JWTError:
        return None

async def require_auth(request: Request) -> dict:
    """Dependency to get current authenticated user"""
    token = None
    
    if 'access_token' in request.cookies:
        auth_cookie = request.cookies.get('access_token')
        if auth_cookie and auth_cookie.startswith('Bearer '):
            token = auth_cookie.split(' ')[1]
    
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    request.state.auth_token = token
    
    user = await get_current_user(request, None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
        
    return user

def require_role(allowed_roles: List[str]):
    async def role_checker(user = Depends(require_auth)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

def log_audit(user_id: int, action: str, target_type: str, target_id: int, meta: dict = None):
    Database.execute_query(
        "INSERT INTO audit_log (user_id, action, target_type, target_id, meta_json) VALUES (?, ?, ?, ?, ?)",
        (user_id, action, target_type, target_id, json.dumps(meta) if meta else None)
    )

def generate_school_code():
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

@app.post("/api/schools/register")
async def register_school(request: Request, response: Response):
    try:
        data = await request.json()
        
        school_code = generate_school_code()
        while Database.execute_query("SELECT id FROM schools WHERE code = ?", (school_code,), fetch_one=True):
            school_code = generate_school_code()
        
        school_id = Database.execute_query(
            "INSERT INTO schools (name, code, admin_email, address, phone, website) VALUES (?, ?, ?, ?, ?, ?)",
            (data["name"], school_code, data["admin_email"], data.get("address"), data.get("phone"), data.get("website"))
        )
        
        password_hash = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user_id = Database.execute_query(
            "INSERT INTO users (school_id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
            (school_id, "Admin User", data["admin_email"], password_hash, "admin")
        )
        
        access_token = create_access_token(data={"sub": user_id})
        
        secure_cookie = True if os.environ.get('ARISTA_ENV') == 'production' else False
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=24 * 60 * 60,
            samesite="lax",
            path="/",
            domain=None,
            secure=secure_cookie
        )
        
        return {
            "message": "School registered successfully", 
            "school_code": school_code,
            "user": {
                "id": user_id,
                "email": data["admin_email"],
                "name": "Admin User",
                "role": "admin",
                "school_id": school_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/me")
async def get_current_user_endpoint(request: Request, user = Depends(require_auth)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_dict = dict(user)
    user_dict.pop("password_hash", None)
    return {"user": user_dict}

@app.get("/api/schools/validate/{school_code}")
async def validate_school_code(school_code: str):
    school = Database.execute_query(
        "SELECT name FROM schools WHERE code = ? AND status = 'active'", 
        (school_code,), 
        fetch_one=True
    )
    
    if school:
        return {"valid": True, "school_name": school["name"]}
    else:
        return {"valid": False}

@app.post("/api/students/register")
async def register_student(request: Request):
    data = await request.json()
    
    school = Database.execute_query(
        "SELECT id, name FROM schools WHERE code = ? AND status = 'active'", 
        (data["school_code"],), 
        fetch_one=True
    )
    
    if not school:
        raise HTTPException(status_code=400, detail="Invalid school code")
    
    existing_user = Database.execute_query(
        "SELECT id FROM users WHERE school_id = ? AND email = ?", 
        (school["id"], data["email"]), 
        fetch_one=True
    )
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered for this school")
    
    password_hash = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    full_name = f"{data['first_name']} {data['last_name']}"
    
    Database.execute_query(
        "INSERT INTO users (school_id, name, email, password_hash, role, grade, section, guardian_name, guardian_phone, medical_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (school["id"], full_name, data["email"], password_hash, "student", data["grade"], data["section"], data["guardian_name"], data["guardian_phone"], data.get("medical_notes"))
    )
    
    return {"message": "Student registered successfully", "school_name": school["name"]}

@app.post("/api/auth/signin")
async def signin(response: Response, request: Request):
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    
    user = Database.execute_query(
        "SELECT u.*, s.name as school_name, s.code as school_code FROM users u JOIN schools s ON u.school_id = s.id WHERE u.email = ?", 
        (email,), 
        fetch_one=True
    )
    
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["id"]})
    
    secure_cookie = True if os.environ.get('ARISTA_ENV') == 'production' else False
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=24 * 60 * 60, 
        samesite="lax",
        secure=secure_cookie
    )
    
    user_data = dict(user)
    user_data.pop("password_hash", None)
    
    response_data = {
        "user": user_data,
        "school": {
            "name": user["school_name"],
            "code": user["school_code"]
        }
    }
    
    return response_data

@app.get("/api/dashboard/school")
async def get_school_dashboard_data(
    request: Request,
    user = Depends(require_role(["admin", "teacher"]))
):
    school_id = user.get("school_id")

    stats = {
        "total_events": 0,
        "total_participants": 0,
        "total_teams": 0,
        "pending_tasks": 0
    }

    try:
        ev = Database.execute_query(
            "SELECT COUNT(*) as count FROM events WHERE school_id = ?",
            (school_id,), fetch_one=True
        )
        stats["total_events"] = ev.get("count", 0) if ev else 0
    except Exception as e:
        print(f"Error counting events: {e}")

    try:
        p = Database.execute_query(
            "SELECT COUNT(*) as count FROM participants WHERE school_id = ?",
            (school_id,), fetch_one=True
        )
        stats["total_participants"] = p.get("count", 0) if p else 0
    except Exception:
        try:
            p = Database.execute_query(
                "SELECT COUNT(*) as count FROM participants p JOIN events e ON p.event_id = e.id WHERE e.school_id = ?",
                (school_id,), fetch_one=True
            )
            stats["total_participants"] = p.get("count", 0) if p else 0
        except Exception as e:
            print(f"Error counting participants: {e}")

    try:
        t = Database.execute_query(
            "SELECT COUNT(*) as count FROM teams t JOIN events e ON t.event_id = e.id WHERE e.school_id = ?",
            (school_id,), fetch_one=True
        )
        stats["total_teams"] = t.get("count", 0) if t else 0
    except Exception as e:
        print(f"Error counting teams: {e}")

    try:
        tt = Database.execute_query(
            "SELECT COUNT(*) as count FROM tasks WHERE school_id = ? AND status = 'pending'",
            (school_id,), fetch_one=True
        )
        stats["pending_tasks"] = tt.get("count", 0) if tt else 0
    except Exception:
        try:
            tt = Database.execute_query(
                "SELECT COUNT(*) as count FROM tasks t JOIN events e ON t.event_id = e.id WHERE e.school_id = ? AND t.status = 'pending'",
                (school_id,), fetch_one=True
            )
            stats["pending_tasks"] = tt.get("count", 0) if tt else 0
        except Exception as e:
            print(f"Error counting pending tasks: {e}")

    upcoming_events = []
    for col in ("start_time", "start_at"):
        try:
            upcoming_events = Database.execute_query(
                f"SELECT * FROM events WHERE school_id = ? AND {col} > datetime('now') ORDER BY {col} LIMIT 5",
                (school_id,), fetch_all=True
            )
            break
        except Exception:
            upcoming_events = []

    announcements = []
    try:
        announcements = Database.execute_query(
            "SELECT * FROM announcements WHERE school_id = ? ORDER BY created_at DESC LIMIT 5",
            (school_id,), fetch_all=True
        )
    except Exception as e:
        print(f"Error fetching announcements: {e}")

    tasks = []
    try:
        tasks = Database.execute_query(
            "SELECT * FROM tasks WHERE school_id = ? AND status = 'pending' ORDER BY due_at LIMIT 5",
            (school_id,), fetch_all=True
        )
    except Exception:
        try:
            tasks = Database.execute_query(
                "SELECT * FROM tasks WHERE school_id = ? AND status = 'pending' ORDER BY due_date LIMIT 5",
                (school_id,), fetch_all=True
            )
        except Exception:
            try:
                tasks = Database.execute_query(
                    "SELECT t.* FROM tasks t JOIN events e ON t.event_id = e.id WHERE e.school_id = ? AND t.status = 'pending' ORDER BY t.due_at LIMIT 5",
                    (school_id,), fetch_all=True
                )
            except Exception as e:
                print(f"Error fetching tasks: {e}")
                tasks = []

    return {
        "stats": stats,
        "upcoming_events": [dict(event) for event in (upcoming_events or [])],
        "announcements": [dict(announcement) for announcement in (announcements or [])],
        "tasks": [dict(task) for task in (tasks or [])]
    }

@app.get("/api/dashboard/student")
async def get_student_dashboard_data(user = Depends(require_role(["student"]))):
    school_id = user["school_id"]
    user_id = user["id"]
    
    stats = {}
    stats["enrolled_events"] = Database.execute_query(
        "SELECT COUNT(*) as count FROM participants p JOIN events e ON p.event_id = e.id WHERE p.user_id = ? AND e.school_id = ?", 
        (user_id, school_id), fetch_one=True
    )["count"]
    
    stats["team_memberships"] = Database.execute_query(
        "SELECT COUNT(*) as count FROM team_members tm JOIN teams t ON tm.team_id = t.id JOIN events e ON t.event_id = e.id WHERE tm.participant_id IN (SELECT id FROM participants WHERE user_id = ?) AND e.school_id = ?", 
        (user_id, school_id), fetch_one=True
    )["count"]
    
    upcoming_events = Database.execute_query(
        "SELECT e.* FROM events e JOIN participants p ON e.id = p.event_id WHERE p.user_id = ? AND e.school_id = ? AND e.start_time > datetime('now') ORDER BY e.start_time LIMIT 5",
        (user_id, school_id), fetch_all=True
    )
    
    announcements = Database.execute_query(
        "SELECT * FROM announcements WHERE school_id = ? ORDER BY created_at DESC LIMIT 5",
        (school_id,), fetch_all=True
    )
    
    teams = Database.execute_query(
        """SELECT t.*, e.title as event_title 
           FROM teams t 
           JOIN events e ON t.event_id = e.id 
           JOIN team_members tm ON t.id = tm.team_id 
           JOIN participants p ON tm.participant_id = p.id 
           WHERE p.user_id = ? AND e.school_id = ?""",
        (user_id, school_id), fetch_all=True
    )
    
    return {
        "stats": stats,
        "upcoming_events": [dict(event) for event in upcoming_events],
        "announcements": [dict(announcement) for announcement in announcements],
        "teams": [dict(team) for team in teams]
    }

@app.post("/api/auth/signout")
async def signout():
    response = JSONResponse(content={"message": "Signed out"})
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=None,
        httponly=True,
        samesite="lax"
    )
    return response

@app.get("/api/me")
async def get_me(request: Request, user = Depends(require_auth)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": user}

@app.post("/api/announcements")
async def create_announcement_top(request: Request, user = Depends(require_role(["admin", "teacher"]))):
    data = await request.json()

    title = data.get('title')
    body = data.get('body') or data.get('message') or data.get('content')

    if not title or not body:
        raise HTTPException(status_code=400, detail='Title and body are required')

    conn = Database.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(announcements)")
        ann_info = cur.fetchall()
        ann_cols = [r[1] for r in ann_info]
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

    cols = []
    vals = []

    if 'school_id' in ann_cols:
        cols.append('school_id')
        vals.append(user.get('school_id'))

    if 'event_id' in ann_cols:
        cols.append('event_id')
        vals.append(data.get('event_id'))

    if 'title' in ann_cols:
        cols.append('title')
        vals.append(title)

    if 'body' in ann_cols:
        cols.append('body')
        vals.append(body)
    if 'content' in ann_cols:
        cols.append('content')
        vals.append(body)

    if 'created_by' in ann_cols:
        cols.append('created_by')
        vals.append(user.get('id'))

    if not cols:
        raise HTTPException(status_code=500, detail='No valid announcement columns available to insert')

    placeholders = ', '.join(['?'] * len(cols))
    sql = f"INSERT INTO announcements ({', '.join(cols)}) VALUES ({placeholders})"

    try:
        announcement_id = Database.execute_query(sql, tuple(vals))
        log_audit(user['id'], 'create', 'announcement', announcement_id)
        return {"id": announcement_id, "message": "Announcement created"}
    except Exception as e:
        print(f"Error creating announcement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events")
async def get_events(
    page: int = 1, 
    limit: int = 10, 
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    user = Depends(get_current_user)
):
    offset = (page - 1) * limit
    where_conditions = []
    params = []
    
    if status:
        where_conditions.append("status = ?")
        params.append(status)
    
    if category:
        where_conditions.append("category = ?")
        params.append(category)
    
    if search:
        where_conditions.append("(name LIKE ? OR title LIKE ? OR description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    try:
        events = []
        total = 0
        for col in ("start_time", "start_at"):
            try:
                rows = Database.execute_query(
                    f"SELECT * FROM events{where_clause} ORDER BY {col} DESC LIMIT ? OFFSET ?",
                    tuple(params + [limit, offset]),
                    fetch_all=True
                )
                total_row = Database.execute_query(
                    f"SELECT COUNT(*) as count FROM events{where_clause}",
                    tuple(params),
                    fetch_one=True
                )
                total = total_row.get('count', 0) if total_row else 0
                events = [dict(r) for r in (rows or [])]
                for ev in events:
                    if 'title' not in ev and 'name' in ev:
                        ev['title'] = ev['name']
                break
            except Exception:
                events = []
                total = 0

        return {
            "events": events,
            "total": total,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        print(f"Error in get_events: {e}")
        return {
            "events": [],
            "total": 0,
            "page": page,
            "limit": limit
        }

@app.post("/api/events")
async def create_event(request: Request, user = Depends(require_role(["admin", "teacher"]))):
    data = await request.json()
    
    required_fields = ["title", "host", "location", "start_at", "end_at", "category"]
    for field in required_fields:
        if not data.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required")
    
    conn = Database.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(events)")
        ev_cols = [r[1] for r in cur.fetchall()]
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

    cols = []
    vals = []

    if 'school_id' in ev_cols:
        cols.append('school_id')
        vals.append(user['school_id'])

    if 'name' in ev_cols:
        cols.append('name')
        vals.append(data['title'])

    if 'title' in ev_cols:
        cols.append('title')
        vals.append(data['title'])

    for c in ('host', 'location', 'category', 'description', 'notes', 'registration_link'):
        if c in ev_cols:
            cols.append(c)
            vals.append(data.get(c, ""))

    if 'start_at' in ev_cols:
        cols.append('start_at')
        vals.append(data.get('start_at'))
    if 'end_at' in ev_cols:
        cols.append('end_at')
        vals.append(data.get('end_at'))
    if 'start_time' in ev_cols and 'start_at' not in ev_cols:
        cols.append('start_time')
        vals.append(data.get('start_at'))
    if 'end_time' in ev_cols and 'end_at' not in ev_cols:
        cols.append('end_time')
        vals.append(data.get('end_at'))

    if 'created_by' in ev_cols:
        cols.append('created_by')
        vals.append(user.get('id'))

    if not cols:
        raise HTTPException(status_code=500, detail="No valid event columns available to insert")

    placeholders = ', '.join(['?'] * len(cols))
    sql = f"INSERT INTO events ({', '.join(cols)}) VALUES ({placeholders})"

    try:
        event_id = Database.execute_query(sql, tuple(vals))
        log_audit(user["id"], "create", "event", event_id)
        return {"id": event_id, "message": "Event created"}
    except Exception as e:
        print(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events/{event_id}")
async def get_event(event_id: int, user = Depends(require_auth)):
    event = Database.execute_query(
        "SELECT * FROM events WHERE id = ?",
        (event_id,),
        fetch_one=True
    )
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return dict(event)

@app.put("/api/events/{event_id}")
async def update_event(event_id: int, request: Request, user = Depends(require_role(["admin", "teacher"]))):
    data = await request.json()
    
    event = Database.execute_query(
        "SELECT * FROM events WHERE id = ?",
        (event_id,),
        fetch_one=True
    )
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    update_fields = []
    params = []
    
    for field in ["title", "host", "location", "start_at", "end_at", "category", "status", "description", "notes", "registration_link"]:
        if field in data:
            update_fields.append(f"{field} = ?")
            params.append(data[field])
    
    if update_fields:
        params.append(event_id)
        Database.execute_query(
            f"UPDATE events SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            tuple(params)
        )
        
        log_audit(user["id"], "update", "event", event_id, data)
    
    return {"message": "Event updated"}

@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int, user = Depends(require_role(["admin"]))):
    event = Database.execute_query(
        "SELECT * FROM events WHERE id = ?",
        (event_id,),
        fetch_one=True
    )
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    Database.execute_query("DELETE FROM events WHERE id = ?", (event_id,))
    log_audit(user["id"], "delete", "event", event_id)
    
    return {"message": "Event deleted"}

@app.get("/api/participants")
async def get_participants(
    page: int = 1,
    limit: int = 20,
    grade: Optional[int] = None,
    section: Optional[str] = None,
    search: Optional[str] = None,
    user = Depends(require_auth)
):
    offset = (page - 1) * limit
    where_conditions = []
    params = []
    
    if grade:
        where_conditions.append("grade = ?")
        params.append(grade)
    
    if section:
        where_conditions.append("section = ?")
        params.append(section)
    
    if search:
        where_conditions.append("(first_name LIKE ? OR last_name LIKE ? OR email LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    
    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    participants = Database.execute_query(
        f"SELECT * FROM participants{where_clause} ORDER BY last_name, first_name LIMIT ? OFFSET ?",
        tuple(params + [limit, offset]),
        fetch_all=True
    )
    
    total = Database.execute_query(
        f"SELECT COUNT(*) as count FROM participants{where_clause}",
        tuple(params),
        fetch_one=True
    )
    
    return {
        "participants": [dict(p) for p in participants],
        "total": total["count"],
        "page": page,
        "pages": (total["count"] + limit - 1) // limit
    }

@app.post("/api/participants")
async def create_participant(request: Request, user = Depends(require_role(["admin", "teacher", "student_coordinator"]))):
    data = await request.json()
    
    required_fields = ["first_name", "last_name", "grade", "section", "guardian_name", "guardian_phone"]
    for field in required_fields:
        if not data.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required")
    
    participant_id = Database.execute_query(
        """INSERT INTO participants (first_name, last_name, grade, section, email, 
           phone, guardian_name, guardian_phone, medical_notes) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data["first_name"], data["last_name"], data["grade"], data["section"],
         data.get("email", ""), data.get("phone", ""), data["guardian_name"],
         data["guardian_phone"], data.get("medical_notes", ""))
    )
    
    log_audit(user["id"], "create", "participant", participant_id)
    
    return {"id": participant_id, "message": "Participant created"}

@app.get("/api/participants/{participant_id}")
async def get_participant(participant_id: int, user = Depends(require_auth)):
    participant = Database.execute_query(
        "SELECT * FROM participants WHERE id = ?",
        (participant_id,),
        fetch_one=True
    )
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    return dict(participant)

@app.put("/api/participants/{participant_id}")
async def update_participant(participant_id: int, request: Request, user = Depends(require_role(["admin", "teacher", "student_coordinator"]))):
    data = await request.json()
    
    participant = Database.execute_query(
        "SELECT * FROM participants WHERE id = ?",
        (participant_id,),
        fetch_one=True
    )
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    update_fields = []
    params = []
    
    for field in ["first_name", "last_name", "grade", "section", "email", "phone", "guardian_name", "guardian_phone", "medical_notes"]:
        if field in data:
            update_fields.append(f"{field} = ?")
            params.append(data[field])
    
    if update_fields:
        params.append(participant_id)
        Database.execute_query(
            f"UPDATE participants SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            tuple(params)
        )
        
        log_audit(user["id"], "update", "participant", participant_id, data)
    
    return {"message": "Participant updated"}

@app.delete("/api/participants/{participant_id}")
async def delete_participant(participant_id: int, user = Depends(require_role(["admin"]))):
    participant = Database.execute_query(
        "SELECT * FROM participants WHERE id = ?",
        (participant_id,),
        fetch_one=True
    )
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    Database.execute_query("DELETE FROM participants WHERE id = ?", (participant_id,))
    log_audit(user["id"], "delete", "participant", participant_id)
    
    return {"message": "Participant deleted"}

@app.get("/api/events/{event_id}/teams")
async def get_event_teams(event_id: int, user = Depends(require_auth)):
    teams = Database.execute_query(
        """SELECT t.*, u.name as coach_name 
           FROM teams t 
           LEFT JOIN users u ON t.coach_user_id = u.id 
           WHERE t.event_id = ?""",
        (event_id,),
        fetch_all=True
    )
    
    return [dict(team) for team in teams]

@app.post("/api/events/{event_id}/teams")
async def create_team(event_id: int, request: Request, user = Depends(require_role(["admin", "teacher"]))):
    data = await request.json()
    
    if not data.get("name"):
        raise HTTPException(status_code=400, detail="Team name is required")
    
    team_id = Database.execute_query(
        "INSERT INTO teams (event_id, name, coach_user_id, max_size, notes) VALUES (?, ?, ?, ?, ?)",
        (event_id, data["name"], data.get("coach_user_id"), 
         data.get("max_size", 10), data.get("notes", ""))
    )
    
    log_audit(user["id"], "create", "team", team_id)
    
    return {"id": team_id, "message": "Team created"}

@app.get("/api/teams/{team_id}/members")
async def get_team_members(team_id: int, user = Depends(require_auth)):
    members = Database.execute_query(
        """SELECT p.*, tm.role 
           FROM participants p 
           JOIN team_members tm ON p.id = tm.participant_id 
           WHERE tm.team_id = ?""",
        (team_id,),
        fetch_all=True
    )
    
    return [dict(member) for member in members]

@app.post("/api/teams/{team_id}/members")
async def add_team_member(team_id: int, request: Request, user = Depends(require_role(["admin", "teacher"]))):
    data = await request.json()
    
    participant_id = data.get("participant_id")
    role = data.get("role", "member")
    
    if not participant_id:
        raise HTTPException(status_code=400, detail="Participant ID is required")
    
    existing = Database.execute_query(
        "SELECT * FROM team_members WHERE team_id = ? AND participant_id = ?",
        (team_id, participant_id),
        fetch_one=True
    )
    
    if existing:
        raise HTTPException(status_code=400, detail="Participant already in team")
    
    Database.execute_query(
        "INSERT INTO team_members (team_id, participant_id, role) VALUES (?, ?, ?)",
        (team_id, participant_id, role)
    )
    
    log_audit(user["id"], "add_member", "team", team_id, {"participant_id": participant_id})
    
    return {"message": "Member added to team"}

@app.delete("/api/teams/{team_id}/members/{participant_id}")
async def remove_team_member(team_id: int, participant_id: int, user = Depends(require_role(["admin", "teacher"]))):
    Database.execute_query(
        "DELETE FROM team_members WHERE team_id = ? AND participant_id = ?",
        (team_id, participant_id)
    )
    
    log_audit(user["id"], "remove_member", "team", team_id, {"participant_id": participant_id})
    
    return {"message": "Member removed from team"}

css_dir = FRONTEND_DIR / "css"
js_dir = FRONTEND_DIR / "js"
static_dir = FRONTEND_DIR

if css_dir.exists():
    app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
else:
    print(f"Warning: static css directory not found: {css_dir}")

if js_dir.exists():
    app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
else:
    print(f"Warning: static js directory not found: {js_dir}")

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    print(f"Warning: static directory not found: {static_dir}")

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("../frontend/favicon.ico", media_type="image/x-icon")

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": None, "active_page": "home"}
    )

@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "user": None, "active_page": "login"}
    )

@app.get("/school_register", response_class=HTMLResponse)
async def read_school_register(request: Request):
    return templates.TemplateResponse(
        "school_register.html",
        {"request": request, "user": None, "active_page": "register"}
    )

@app.get("/student_register", response_class=HTMLResponse)
async def read_student_register():
    return FileResponse("../frontend/html/student_register.html")

@app.get("/school_dashboard", response_class=HTMLResponse)
async def read_school_dashboard(
    request: Request,
    user: dict = Depends(require_auth)
):
    try:
        school = Database.execute_query(
            """
            SELECT 
                id, name, code, admin_email, 
                address, phone, website, status
            FROM schools 
            WHERE id = ?
            """,
            (user.get("school_id"),),
            fetch_one=True
        )
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
        
        school_data = dict(school) if hasattr(school, 'keys') else school
        
        required_fields = ['id', 'name', 'code', 'admin_email', 'status']
        for field in required_fields:
            if field not in school_data:
                school_data[field] = ""
        
        return templates.TemplateResponse(
            "school_dashboard.html",
            {
                "request": request, 
                "user": user, 
                "active_page": "dashboard",
                "school": school_data
            }
        )
    except Exception as e:
        import traceback
        print(f"Error in read_school_dashboard: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/student_dashboard", response_class=HTMLResponse)
async def read_student_dashboard(request: Request, user = Depends(get_current_user)):
    # `get_current_user` returns a dict; use dict access to check role
    if not user or (user.get('role') if isinstance(user, dict) else getattr(user, 'role', None)) != 'student':
        raise HTTPException(status_code=403, detail="Access denied")
        
    return templates.TemplateResponse(
        "student_dashboard.html",
        {"request": request, "user": user, "active_page": "student_dashboard"}
    )

@app.get("/events", response_class=HTMLResponse)
async def read_events(request: Request, user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    return templates.TemplateResponse(
        "events.html",
        {"request": request, "user": user, "active_page": "events"}
    )


@app.get("/events/{event_id}", response_class=HTMLResponse)
async def read_event_detail(request: Request, event_id: int, user = Depends(get_current_user)):
    # Serve the same events HTML page for a specific event URL so client-side JS
    # can read the event id from the path and load details via the API.
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return templates.TemplateResponse(
        "events.html",
        {"request": request, "user": user, "active_page": "events", "selected_event_id": event_id}
    )

@app.get("/participants", response_class=HTMLResponse)
async def read_participants(request: Request, user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    return templates.TemplateResponse(
        "participants.html",
        {"request": request, "user": user, "active_page": "participants"}
    )

@app.get("/teams", response_class=HTMLResponse)
async def read_teams(request: Request, user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    return templates.TemplateResponse(
        "teams.html",
        {"request": request, "user": user, "active_page": "teams"}
    )

@app.get("/schedules", response_class=HTMLResponse)
async def read_schedules(request: Request, user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    return templates.TemplateResponse(
        "schedules.html",
        {"request": request, "user": user, "active_page": "schedules"}
    )

@app.get("/tasks", response_class=HTMLResponse)
async def read_tasks(request: Request, user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    return templates.TemplateResponse(
        "tasks.html",
        {"request": request, "user": user, "active_page": "tasks"}
    )

@app.get("/announcements", response_class=HTMLResponse)
async def read_announcements(request: Request, user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    return templates.TemplateResponse(
        "announcements.html",
        {"request": request, "user": user, "active_page": "announcements"}
    )

@app.get("/files", response_class=HTMLResponse)
async def read_files(request: Request, user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    return templates.TemplateResponse(
        "files.html",
        {"request": request, "user": user, "active_page": "files"}
    )

@app.get("/admin", response_class=HTMLResponse)
async def read_admin(request: Request, user = Depends(get_current_user)):
    if not user or user.role != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
        
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "user": user, "active_page": "admin"}
    )

@app.get("/features", response_class=HTMLResponse)
async def read_features(request: Request):
    return templates.TemplateResponse(
        "features.html",
        {"request": request, "user": None, "active_page": "features"}
    )
