document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('studentRegisterForm');
    const schoolCodeInput = document.getElementById('schoolCode');
    
    if (form) {
        form.addEventListener('submit', handleStudentRegistration);
    }
    
    if (schoolCodeInput) {
        schoolCodeInput.addEventListener('blur', validateSchoolCode);
        schoolCodeInput.addEventListener('input', hideSchoolInfo);
    }
});

async function validateSchoolCode() {
    const schoolCode = document.getElementById('schoolCode').value.trim();
    const schoolInfo = document.getElementById('schoolInfo');
    
    if (!schoolCode) {
        schoolInfo.style.display = 'none';
        return;
    }
    
    try {
        const response = await api.get(`/schools/validate/${schoolCode}`);
        if (response.valid) {
            schoolInfo.textContent = `School found: ${response.school_name}`;
            schoolInfo.style.display = 'block';
        } else {
            schoolInfo.style.display = 'none';
            showToast('Invalid school code', 'error');
        }
    } catch (error) {
        schoolInfo.style.display = 'none';
        showToast('Unable to validate school code', 'error');
    }
}

function hideSchoolInfo() {
    document.getElementById('schoolInfo').style.display = 'none';
}

async function handleStudentRegistration(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const studentData = Object.fromEntries(formData);
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoading = submitBtn.querySelector('.btn-loading');
    
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'flex';
    
    try {
        const response = await api.post('/students/register', studentData);
        
        document.querySelector('.register-form-container').style.display = 'none';
        const successMessage = document.getElementById('successMessage');
        document.getElementById('schoolName').textContent = response.school_name;
        successMessage.style.display = 'block';
        
        showToast('Student registration successful!', 'success');
    } catch (error) {
        showToast(error.message || 'Registration failed', 'error');
        
        submitBtn.disabled = false;
        btnText.style.display = 'block';
        btnLoading.style.display = 'none';
    }
}
