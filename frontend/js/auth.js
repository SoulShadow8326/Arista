document.addEventListener('DOMContentLoaded', async function() {
    const loginForm = document.getElementById('loginForm');
    const loginLoading = document.getElementById('loginLoading');
    
    document.body.style.display = 'block';
    
    if (window.location.pathname === '/login') {
        const token = localStorage.getItem('token');
        if (token) {
            try {
                const user = await api.getMe();
                if (user && user.user) {
                    window.location.href = '/school_dashboard';
                    return;
                }
            } catch (error) {
                localStorage.removeItem('token');
                console.log('Invalid token, showing login form');
            }
        }
    }
    
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Form submission started');
            
            const form = e.target;
            const email = form.email.value;
            const password = form.password.value;
            
            console.log('Form values:', { email, password });
            
            if (!email || !password) {
                showToast('Please enter both email and password', 'error');
                return;
            }
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const btnText = submitBtn.querySelector('.btn-text');
            
            submitBtn.disabled = true;
            btnText.style.opacity = '0';
            loginLoading.style.display = 'inline-block';
            
            try {
                console.log('Attempting to sign in with:', { email });
                const response = await api.signIn(email, password);
                console.log('Sign in response:', response);
                
                if (response && response.access_token) {
                    localStorage.setItem('token', response.access_token);
                }
                
                showToast('Signed in successfully', 'success');
                setTimeout(() => {
                    window.location.href = '/school_dashboard';
                }, 500);
            } catch (error) {
                console.error('Login error:', error);
                showToast(error.message || 'Login failed. Please check your credentials and try again.', 'error');
                
                submitBtn.disabled = false;
                btnText.style.opacity = '1';
                loginLoading.style.display = 'none';
                loginForm.removeAttribute('data-submitting');
            }
        });
    }
});

window.signOut = async function() {
    try {
        await api.post('/auth/signout');
    } catch (error) {
        console.error('Error during sign out:', error);
    } finally {
        localStorage.removeItem('token');
        window.location.href = '/login';
    }
};
