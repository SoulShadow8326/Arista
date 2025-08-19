let currentEventFilter = '';

document.addEventListener('DOMContentLoaded', async function() {
    try {
        const userResponse = await api.getMe();
        document.getElementById('userName').textContent = userResponse.user.name;
        
        if (userResponse.user.role === 'admin') {
            document.querySelector('.admin-only').style.display = 'block';
        }
        
        setupEventListeners();
        await loadEvents();
        loadTeams();
    } catch (error) {
        window.location.href = '/login';
    }
});

function setupEventListeners() {
    document.getElementById('signOutBtn').addEventListener('click', async function() {
        try {
            await api.signOut();
            window.location.href = '/login';
        } catch (error) {
            window.location.href = '/login';
        }
    });

    document.querySelectorAll('[data-dropdown-menu] [data-value]').forEach(item => {
        item.addEventListener('click', function() {
            const dropdown = this.closest('.dropdown');
            if (dropdown) {
                const value = this.getAttribute('data-value');
                const displayElement = dropdown.querySelector('[data-dropdown-trigger] span');
                if (displayElement) {
                    displayElement.textContent = this.textContent;
                    currentEventFilter = value;
                    loadTeams();
                }
            }
        });
    });

    document.getElementById('createTeamForm').addEventListener('submit', handleCreateTeam);
}

async function loadEvents() {
    try {
        const response = await api.get('/events?status=active');
        const eventFilterOptions = document.getElementById('eventFilterOptions');
        const teamEventSelect = document.getElementById('teamEvent');
        
        eventFilterOptions.innerHTML = '';
        teamEventSelect.innerHTML = '<option value="">Select Event</option>';
        
        (response.events || []).forEach(event => {
            const filterOption = document.createElement('button');
            filterOption.className = 'dropdown-item';
            filterOption.setAttribute('data-value', event.id);
            filterOption.textContent = event.title;
            eventFilterOptions.appendChild(filterOption);
            
            const option = new Option(event.title, event.id);
            teamEventSelect.add(option);
        });
    } catch (error) {
        console.error('Events load error:', error);
    }
}

async function loadTeams() {
    try {
        const events = await api.get('/events?status=active');
        let allTeams = [];
        
        for (const event of events.events || []) {
            if (currentEventFilter && event.id.toString() !== currentEventFilter) {
                continue;
            }
            
            const teams = await api.get(`/events/${event.id}/teams`);
            for (const team of teams) {
                const members = await api.get(`/teams/${team.id}/members`);
                allTeams.push({
                    ...team,
                    event_title: event.title,
                    members: members
                });
            }
        }
        
        renderTeams(allTeams);
    } catch (error) {
        console.error('Teams load error:', error);
        showToast('Failed to load teams', 'error');
    }
}

function renderTeams(teams) {
    const container = document.getElementById('teamsList');
    
    if (teams.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🏆</div>
                <div class="empty-state-title">No Teams Found</div>
                <div class="empty-state-message">Create teams to organize participants for events.</div>
                <button class="btn btn-primary" onclick="showCreateTeamModal()">Create Your First Team</button>
            </div>
        `;
        return;
    }

    container.innerHTML = teams.map(team => {
        const memberAvatars = team.members.slice(0, 6).map(member => {
            const initials = `${member.first_name[0]}${member.last_name[0]}`.toUpperCase();
            const captainClass = member.role === 'captain' ? ' captain' : '';
            return `<div class="member-avatar${captainClass}" title="${member.first_name} ${member.last_name}">${initials}</div>`;
        }).join('');
        
        const extraCount = team.members.length > 6 ? `<div class="member-avatar">+${team.members.length - 6}</div>` : '';
        
        return `
            <div class="team-card fade-in" onclick="viewTeam(${team.id})">
                <div class="team-header">
                    <div class="team-name">${team.name}</div>
                    <div class="team-event">${team.event_title}</div>
                </div>
                
                <div class="team-info">
                    <div class="team-info-item">
                        <span class="team-info-icon">👨‍🏫</span>
                        <span>Coach: ${team.coach_name || 'Unassigned'}</span>
                    </div>
                    <div class="team-info-item">
                        <span class="team-info-icon"></span>
                        <span>${team.members.length} / ${team.max_size} members</span>
                    </div>
                </div>
                
                ${team.members.length > 0 ? `
                    <div class="team-members">
                        <div class="members-title">Team Members</div>
                        <div class="members-list">
                            ${memberAvatars}
                            ${extraCount}
                        </div>
                    </div>
                ` : ''}
                
                ${team.notes ? `
                    <div class="team-notes">${team.notes}</div>
                ` : ''}
                
                <div class="team-stats">
                    <div class="team-size">
                        ${team.members.length} members
                    </div>
                    <div class="team-actions">
                        <button class="action-btn" onclick="event.stopPropagation(); editTeam(${team.id})" title="Edit Team">✏️</button>
                        <button class="action-btn" onclick="event.stopPropagation(); manageMembers(${team.id})" title="Manage Members"></button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

async function handleCreateTeam(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const teamData = Object.fromEntries(formData);

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="loading"></div> Creating...';

    try {
        await api.post(`/events/${teamData.event_id}/teams`, teamData);
        closeModal('createTeamModal');
        e.target.reset();
        loadTeams();
        showToast('Team created successfully', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function showCreateTeamModal() {
    showModal('createTeamModal');
}

function viewTeam(teamId) {
    window.location.href = `/teams/${teamId}`;
}

function editTeam(teamId) {
    console.log('Edit team:', teamId);
}

function manageMembers(teamId) {
    console.log('Manage members for team:', teamId);
}
