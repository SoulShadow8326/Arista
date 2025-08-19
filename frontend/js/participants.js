let currentPage = 1;
let selectedParticipants = new Set();

document.addEventListener('DOMContentLoaded', async function() {
    try {
        const userResponse = await api.getMe();
        document.getElementById('userName').textContent = userResponse.user.name;
        
        if (userResponse.user.role === 'admin') {
            document.querySelector('.admin-only').style.display = 'block';
        }
        
        setupEventListeners();
        loadParticipants();
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

    document.getElementById('participantSearch').addEventListener('input', debounce(() => {
        currentPage = 1;
        loadParticipants();
    }, 300));

    document.getElementById('gradeFilter').addEventListener('change', () => {
        currentPage = 1;
        loadParticipants();
    });

    document.getElementById('sectionFilter').addEventListener('change', () => {
        currentPage = 1;
        loadParticipants();
    });

    document.getElementById('createParticipantForm').addEventListener('submit', handleCreateParticipant);
}

async function loadParticipants(page = 1) {
    try {
        const search = document.getElementById('participantSearch').value;
        const grade = document.getElementById('gradeFilter').value;
        const section = document.getElementById('sectionFilter').value;
        
        const params = new URLSearchParams({
            page: page.toString(),
            limit: '20'
        });
        
        if (search) params.append('search', search);
        if (grade) params.append('grade', grade);
        if (section) params.append('section', section);

        const response = await api.get(`/participants?${params}`);
        renderParticipants(response.participants || []);
        renderPagination(response.page, response.pages);
        currentPage = page;
    } catch (error) {
        console.error('Participants load error:', error);
        showToast('Failed to load participants', 'error');
    }
}

function renderParticipants(participants) {
    const container = document.getElementById('participantsList');
    
    if (participants.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon"></div>
                <div class="empty-state-title">No Participants Found</div>
                <div class="empty-state-message">Try adjusting your search criteria or add a new participant.</div>
                <button class="btn btn-primary" onclick="showCreateParticipantModal()">Add Your First Participant</button>
            </div>
        `;
        return;
    }

    container.innerHTML = participants.map(participant => {
        const initials = `${participant.first_name[0]}${participant.last_name[0]}`.toUpperCase();
        return `
            <div class="participant-card fade-in" onclick="viewParticipant(${participant.id})">
                <input type="checkbox" class="participant-checkbox" data-id="${participant.id}" onclick="event.stopPropagation(); toggleParticipantSelection(${participant.id})">
                
                <div class="participant-header">
                    <div class="participant-avatar">${initials}</div>
                    <div class="participant-info">
                        <div class="participant-name">${participant.first_name} ${participant.last_name}</div>
                        <div class="participant-grade">Grade ${participant.grade}${participant.section}</div>
                    </div>
                </div>
                
                <div class="participant-details">
                    ${participant.email ? `
                        <div class="participant-detail-item">
                            <span class="participant-detail-icon">📧</span>
                            <span>${participant.email}</span>
                        </div>
                    ` : ''}
                    ${participant.phone ? `
                        <div class="participant-detail-item">
                            <span class="participant-detail-icon">📱</span>
                            <span>${participant.phone}</span>
                        </div>
                    ` : ''}
                </div>
                
                <div class="participant-contact">
                    <div class="contact-title">Guardian Information</div>
                    <div class="contact-info">
                        <div class="contact-item">${participant.guardian_name}</div>
                        <div class="contact-item">${participant.guardian_phone}</div>
                    </div>
                </div>
                
                ${participant.medical_notes ? `
                    <div class="medical-notes">
                        <div class="medical-notes-title">Medical Notes</div>
                        <div class="medical-notes-text">${participant.medical_notes}</div>
                    </div>
                ` : ''}
                
                <div class="participant-actions">
                    <div class="participant-status">
                        <span class="status-badge status-active">Active</span>
                    </div>
                    <button class="menu-button" onclick="event.stopPropagation(); showParticipantMenu(${participant.id})">⋮</button>
                </div>
            </div>
        `;
    }).join('');
}

function renderPagination(currentPage, totalPages) {
    const container = document.getElementById('participantsPagination');
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let pagination = '';
    
    if (currentPage > 1) {
        pagination += `<button onclick="loadParticipants(${currentPage - 1})">← Previous</button>`;
    }

    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);

    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        pagination += `<button class="${activeClass}" onclick="loadParticipants(${i})">${i}</button>`;
    }

    if (currentPage < totalPages) {
        pagination += `<button onclick="loadParticipants(${currentPage + 1})">Next →</button>`;
    }

    container.innerHTML = pagination;
}

async function handleCreateParticipant(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const participantData = Object.fromEntries(formData);

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="loading"></div> Adding...';

    try {
        await api.post('/participants', participantData);
        closeModal('createParticipantModal');
        e.target.reset();
        loadParticipants(currentPage);
        showToast('Participant added successfully', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function showCreateParticipantModal() {
    showModal('createParticipantModal');
}

function viewParticipant(participantId) {
    window.location.href = `/participants/${participantId}`;
}

function toggleParticipantSelection(participantId) {
    if (selectedParticipants.has(participantId)) {
        selectedParticipants.delete(participantId);
    } else {
        selectedParticipants.add(participantId);
    }
    updateBulkActions();
}

function updateBulkActions() {
    const bulkActions = document.getElementById('bulkActions');
    if (!bulkActions) return;
    
    if (selectedParticipants.size > 0) {
        bulkActions.classList.add('show');
    } else {
        bulkActions.classList.remove('show');
    }
}

function exportParticipants() {
    window.open('/api/reports/participants/csv', '_blank');
}

function showParticipantMenu(participantId) {
    console.log('Show menu for participant:', participantId);
}
