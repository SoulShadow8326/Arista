let currentPage = 1;
let currentFilters = {};

document.addEventListener('DOMContentLoaded', async function() {
    try {
        const userResponse = await api.getMe();
        document.getElementById('userName').textContent = userResponse.user.name;
        
        if (userResponse.user.role === 'admin') {
            document.querySelector('.admin-only').style.display = 'block';
        }
        
    try { setupEventListeners(); } catch (e) { console.warn('setupEventListeners failed', e); }
        loadEvents();
    } catch (error) {
    console.warn('User not authenticated, continuing as guest:', error);
    const userNameEl = document.getElementById('userName');
    if (userNameEl) userNameEl.textContent = 'Guest';
    try { setupEventListeners(); } catch (e) { console.warn('setupEventListeners failed', e); }
    loadEvents();
    }
});

function setupEventListeners() {
    const signOutBtn = document.getElementById('signOutBtn');
    if (signOutBtn && signOutBtn.addEventListener) {
        signOutBtn.addEventListener('click', async function() {
            try {
                await api.signOut();
            } finally {
                window.location.href = '/login';
            }
        });
    }

    const eventSearchEl = document.getElementById('eventSearch');
    if (eventSearchEl && eventSearchEl.addEventListener) {
        eventSearchEl.addEventListener('input', debounce(() => {
            currentPage = 1;
            loadEvents();
        }, 300));
    }

    const dropdownItems = document.querySelectorAll && document.querySelectorAll('[data-dropdown-menu] [data-value]');
    if (dropdownItems && dropdownItems.forEach) {
        dropdownItems.forEach(item => {
            if (!item || !item.addEventListener) return;
            item.addEventListener('click', function() {
                const dropdown = this.closest && this.closest('.dropdown');
                if (dropdown) {
                    const value = this.getAttribute('data-value');
                    const displayElement = dropdown.querySelector && dropdown.querySelector('[data-dropdown-trigger] span');
                    if (displayElement) displayElement.textContent = this.textContent;
                    if (dropdown.querySelector('[data-value="draft"]')) {
                        currentFilters.status = value || undefined;
                    } else {
                        currentFilters.category = value || undefined;
                    }
                    currentPage = 1;
                    loadEvents();
                }
            });
        });
    }

    const createEventForm = document.getElementById('createEventForm');
    if (createEventForm && createEventForm.addEventListener) {
        createEventForm.addEventListener('submit', handleCreateEvent);
    }
}

async function loadEvents(page = 1) {
    try {
    const searchEl = document.getElementById('eventSearch');
    const search = searchEl ? searchEl.value : '';
        const filters = {
            search,
            ...currentFilters
        };
        
        const params = new URLSearchParams({
            page: page.toString(),
            limit: '12',
            ...(filters.search && { search: filters.search }),
            ...(filters.status && { status: filters.status }),
            ...(filters.category && { category: filters.category })
        });

        const response = await api.get(`/events?${params}`);
    renderEvents(response.events || []);
    renderPagination(response.page, response.pages);
        currentPage = page;
    } catch (error) {
        console.error('Events load error:', error);
        showToast('Failed to load events', 'error');
    }
}

function renderEvents(events) {
    const container = document.getElementById('eventsList');
    if (!container) return;

    if (!events || events.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚀</div>
                <div class="empty-state-title">No Events Found</div>
                <div class="empty-state-message">Try adjusting your search criteria or create a new event.</div>
                <button class="btn btn-primary" onclick="showCreateEventModal()">Create Your First Event</button>
            </div>
        `;
        return;
    }

    container.innerHTML = events.map(event => `
        <div class="event-card fade-in" onclick="viewEvent(${event.id})">
            <div class="event-title">${event.title}</div>
            <div class="event-meta">
                <span class="meta-tag status-${event.status}">${event.status}</span>
                <span class="meta-tag category">${event.category}</span>
            </div>
            <div class="event-description">${event.description || 'No description available'}</div>
            <div class="event-details">
                <div class="event-detail-item">
                    <span class="event-detail-icon">⚀</span>
                    <span>${event.location}</span>
                </div>
                <div class="event-detail-item">
                    <span class="event-detail-icon">⚀</span>
                    <span>${event.host}</span>
                </div>
                <div class="event-detail-item">
                    <span class="event-detail-icon">⚀</span>
                    <span>${formatDate(event.start_at)}</span>
                </div>
                <div class="event-detail-item">
                    <span class="event-detail-icon">⚀</span>
                    <span>${formatDate(event.end_at)}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function renderPagination(currentPage, totalPages) {
    const container = document.getElementById('eventsPagination');
    if (!container) return;
    
    if (!totalPages || totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let pagination = '';
    
    if (currentPage > 1) {
        pagination += `<button onclick="loadEvents(${currentPage - 1})">← Previous</button>`;
    }

    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);

    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        pagination += `<button class="${activeClass}" onclick="loadEvents(${i})">${i}</button>`;
    }

    if (currentPage < totalPages) {
        pagination += `<button onclick="loadEvents(${currentPage + 1})">Next →</button>`;
    }

    container.innerHTML = pagination;
}

async function handleCreateEvent(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);

    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn ? submitBtn.textContent : '';
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="loading"></div> Creating...';
    }

    try {
        const date = data.date || data.eventDate || document.getElementById('eventDate') && document.getElementById('eventDate').value;
        const time = data.time || data.eventTime || document.getElementById('eventTime') && document.getElementById('eventTime').value;
        const start_at = date ? (time ? `${date}T${time}` : `${date}T00:00:00`) : new Date().toISOString();
        let end_at = start_at;
        if (data.end_time) {
            end_at = data.end_time;
        } else {
            const dt = new Date(start_at);
            dt.setHours(dt.getHours() + 2);
            end_at = dt.toISOString();
        }

        const payload = {
            title: data.title || data.eventTitle || data.name || '',
            host: data.host || document.getElementById('userName') && document.getElementById('userName').textContent || 'Host',
            location: data.location || data.eventLocation || '',
            start_at: start_at,
            end_at: end_at,
            category: data.category || 'general',
            description: data.description || data.eventDescription || ''
        };

        await api.post('/events', payload);
        closeModal('createEventModal');
        e.target.reset();
        loadEvents(currentPage);
        showToast('Event created successfully', 'success');
    } catch (error) {
        showToast(error.message || 'Failed to create event', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }
}

function showCreateEventModal() {
    showModal('createEventModal');
}

function viewEvent(eventId) {
    window.location.href = `/events/${eventId}`;
}
