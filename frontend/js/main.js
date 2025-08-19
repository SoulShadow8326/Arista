document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const headerContent = document.querySelector('.header-content') || document.querySelector('.nav-container');
    
    if (mobileMenuBtn && headerContent) {
        mobileMenuBtn.addEventListener('click', function() {
            headerContent.classList.toggle('mobile-menu-open');
        });

        document.addEventListener('click', function(e) {
            const hc = document.querySelector('.header-content') || document.querySelector('.nav-container');
            if (hc && !hc.contains(e.target) && !e.target.classList.contains('mobile-menu-btn')) {
                hc.classList.remove('mobile-menu-open');
            }
        });
    }
    
    const signOutBtn = document.getElementById('signOutBtn');
    if (signOutBtn) {
        signOutBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            try {
                await api.signOut();
                window.location.href = '/';
            } catch (error) {
                console.error('Sign out failed:', error);
                showToast('Failed to sign out. Please try again.', 'error');
            }
        });
    }
});

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    const existingTimeout = toast.dataset.timeout;
    if (existingTimeout) {
        clearTimeout(existingTimeout);
    }
    
    toast.textContent = message;
    toast.className = 'toast';
    toast.classList.add(type);
    
    setTimeout(() => {
        toast.classList.add('show');
        
        const timeout = setTimeout(() => {
            toast.classList.remove('show');
        }, 5000);
        
        toast.dataset.timeout = timeout;
    }, 100);
}

document.addEventListener('click', function(e) {
    const target = e.target;
    if (target instanceof Element && target.classList.contains('toast')) {
        target.classList.remove('show');
    }
});

document.addEventListener('submit', async function(e) {
    const form = e.target.closest('form');
    if (!form) return;
    
    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;
    
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Processing...';
    
    try {
        if (form.dataset.api) {
            e.preventDefault();
            const formData = new FormData(form);
            const response = await fetch(form.action || form.dataset.api, {
                method: form.method || 'POST',
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Something went wrong');
            }
            
            showToast(data.message || 'Operation successful', 'success');
            
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1500);
            }
            
            if (form.dataset.resetOnSuccess) {
                form.reset();
            }
        }
    } catch (error) {
        console.error('Form submission error:', error);
        showToast(error.message || 'An error occurred', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
});
