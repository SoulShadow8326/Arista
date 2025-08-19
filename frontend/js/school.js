document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('schoolRegisterForm');
    if (form) {
        form.addEventListener('submit', handleSchoolRegistration);
    }
});

async function handleSchoolRegistration(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const schoolData = Object.fromEntries(formData);
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoading = submitBtn.querySelector('.btn-loading');
    
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'flex';
    
    try {
        const response = await fetch('/api/schools/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include', 
            body: JSON.stringify(schoolData)
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Registration failed');
        }
        
        showToast('School registered successfully!', 'success');
        
        if (data.user) {
            localStorage.setItem('user', JSON.stringify(data.user));
        }
        if (data.school_code) {
            localStorage.setItem('school_code', data.school_code);
        }
        
        setTimeout(() => {
            window.location.href = '/school_dashboard';
        }, 1500);
    } catch (error) {
        console.error('Registration error:', error);
        showToast(error.message || 'Registration failed', 'error');
        
        submitBtn.disabled = false;
        btnText.style.display = 'block';
        btnLoading.style.display = 'none';
    }
}
