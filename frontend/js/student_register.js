document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('studentRegisterForm');
    
    const dropdowns = document.querySelectorAll('.dropdown[data-dropdown]');
    dropdowns.forEach(dropdown => {
        const trigger = dropdown.querySelector('[data-dropdown-trigger]');
        const menu = dropdown.querySelector('[data-dropdown-menu]');
        const hiddenInput = dropdown.querySelector('input[type="hidden"]');
        const displaySpan = dropdown.querySelector('span');
        
        if (trigger && menu && hiddenInput && displaySpan) {
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                dropdown.classList.toggle('dropdown-open');
            });

            menu.querySelectorAll('.dropdown-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    const value = item.getAttribute('data-value');
                    const text = item.textContent;
                    
                    hiddenInput.value = value;
                    displaySpan.textContent = text;
                    
                    if (value) {
                        hiddenInput.setCustomValidity('');
                    } else {
                        hiddenInput.setCustomValidity('Please select a grade');
                    }
                    
                    dropdown.classList.remove('dropdown-open');
                });
            });
            
            document.addEventListener('click', (e) => {
                if (!dropdown.contains(e.target)) {
                    dropdown.classList.remove('dropdown-open');
                }
            });
        }
    });
    
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            
            try {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';
                
                const formData = new FormData(form);
                const response = await fetch('/api/students/register', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('schoolName').textContent = data.school_name || 'your school';
                    form.style.display = 'none';
                    document.getElementById('successMessage').style.display = 'block';
                } else {
                    throw new Error(data.message || 'Registration failed');
                }
            } catch (error) {
                console.error('Registration error:', error);
                showToast(error.message || 'Registration failed. Please try again.', 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }
});

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = 'toast';
    toast.classList.add(type);
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 5000);
}
