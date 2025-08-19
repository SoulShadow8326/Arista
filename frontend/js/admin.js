let currentAuditPage = 1;

document.addEventListener('DOMContentLoaded', async function() {
    try {
        const userResponse = await api.getMe();
        document.getElementById('userName').textContent = userResponse.user.name;
        
        if (userResponse.user.role !== 'admin') {
            showToast('Access denied - Admin role required', 'error');
            window.location.href = '/';
            return;
        }
        
        setupEventListeners();
        loadSystemStats();
        loadAuditLog();
        loadUsers();
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

    document.getElementById('auditFilter').addEventListener('change', () => {
        currentAuditPage = 1;
        loadAuditLog();
    });

    document.getElementById('createUserForm').addEventListener('submit', handleCreateUser);
}

async function loadSystemStats() {
    try {
        const [events, participants, users] = await Promise.all([
            api.get('/events'),
            api.get('/participants'),
            api.get('/audit?limit=1')
        ]);

        const stats = {
            totalEvents: events.total || 0,
            activeEvents: events.events?.filter(e => e.status === 'active').length || 0,
            totalParticipants: participants.total || 0,
            totalUsers: 5
        };

        renderSystemStats(stats);
    } catch (error) {
        console.error('System stats load error:', error);
    }
}

function renderSystemStats(stats) {
    const container = document.getElementById('systemStats');
    container.innerHTML = `
        <div class="stat-item">
            <div class="stat-number">${stats.totalEvents}</div>
            <div class="stat-label">Total Events</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">${stats.activeEvents}</div>
            <div class="stat-label">Active Events</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">${stats.totalParticipants}</div>
            <div class="stat-label">Participants</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">${stats.totalUsers}</div>
            <div class="stat-label">Users</div>
        </div>
    `;
}

async function loadAuditLog(page = 1) {
    try {
        const filter = document.getElementById('auditFilter').value;
        const params = new URLSearchParams({
            page: page.toString(),
            limit: '20'
        });
        
        if (filter) params.append('action', filter);

        const response = await api.get(`/audit?${params}`);
        renderAuditLog(response.logs || []);
        renderAuditPagination(response.page, response.pages);
        currentAuditPage = page;
    } catch (error) {
        console.error('Audit log load error:', error);
    }
}

function renderAuditLog(logs) {
    const container = document.getElementById('auditLog');
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="empty-message">No audit logs found</div>';
        return;
    }

    container.innerHTML = logs.map(log => `
        <div class="audit-item slide-in-left">
            <div class="audit-header">
                <div class="audit-user">${log.user_name}</div>
                <div class="audit-time">${formatDate(log.created_at)}</div>
            </div>
            <div class="audit-action">${log.action} ${log.target_type}</div>
            <div class="audit-target">Target ID: ${log.target_id}</div>
        </div>
    `).join('');
}

function renderAuditPagination(currentPage, totalPages) {
    const container = document.getElementById('auditPagination');
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let pagination = '';
    
    if (currentPage > 1) {
        pagination += `<button onclick="loadAuditLog(${currentPage - 1})">← Previous</button>`;
    }

    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);

    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        pagination += `<button class="${activeClass}" onclick="loadAuditLog(${i})">${i}</button>`;
    }

    if (currentPage < totalPages) {
        pagination += `<button onclick="loadAuditLog(${currentPage + 1})">Next →</button>`;
    }

    container.innerHTML = pagination;
}

async function loadUsers() {
    const mockUsers = [
        { id: 1, name: 'Admin User', email: 'admin@school.edu', role: 'admin' },
        { id: 2, name: 'John Smith', email: 'john.smith@school.edu', role: 'teacher' },
        { id: 3, name: 'Sarah Johnson', email: 'sarah.johnson@school.edu', role: 'teacher' },
        { id: 4, name: 'Mike Chen', email: 'mike.chen@school.edu', role: 'student_coordinator' },
        { id: 5, name: 'Lisa Brown', email: 'lisa.brown@school.edu', role: 'viewer' }
    ];
    
    renderUsers(mockUsers);
}

function renderUsers(users) {
    const container = document.getElementById('usersList');
    
    if (users.length === 0) {
        container.innerHTML = '<div class="empty-message">No users found</div>';
        return;
    }

    container.innerHTML = users.map(user => {
        const initials = user.name.split(' ').map(n => n[0]).join('').toUpperCase();
        return `
            <div class="user-item slide-in-left">
                <div class="user-info">
                    <div class="user-avatar">${initials}</div>
                    <div class="user-details">
                        <div class="user-name">${user.name}</div>
                        <div class="user-email">${user.email}</div>
                    </div>
                </div>
                <div class="user-role role-${user.role}">${user.role.replace('_', ' ')}</div>
                <div class="user-actions">
                    <button class="action-btn" onclick="editUser(${user.id})" title="Edit User">✏️</button>
                    <button class="action-btn" onclick="deleteUser(${user.id})" title="Delete User">🗑️</button>
                </div>
            </div>
        `;
    }).join('');
}

async function handleCreateUser(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const userData = Object.fromEntries(formData);

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="loading"></div> Creating...';

    try {
        showToast('User creation not implemented in demo', 'info');
        closeModal('createUserModal');
        e.target.reset();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function showCreateUserModal() {
    showModal('createUserModal');
}

function editUser(userId) {
    showToast('Edit user functionality not implemented in demo', 'info');
}

function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user?')) {
        showToast('Delete user functionality not implemented in demo', 'info');
    }
}

function exportAuditLog() {
    showToast('Audit log export not implemented in demo', 'info');
}

function exportUsers() {
    showToast('User export not implemented in demo', 'info');
}
