// Password toggle functionality
const toggleBtn = document.getElementById('toggleBtn');
const passwordInput = document.getElementById('password');
const toggleText = document.getElementById('toggle-text');

if (toggleBtn && passwordInput && toggleText) {
    toggleBtn.addEventListener('click', function() {
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            toggleText.textContent = 'HIDE';
        } else {
            passwordInput.type = 'password';
            toggleText.textContent = 'SHOW';
        }
    });
}

// Form submission
const loginForm = document.getElementById('loginForm');

if (loginForm) {
    loginForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        console.log('Login attempt:', username); // For debugging
        
        // Add your login validation here
        if (username && password) {
            console.log('Redirecting to dashboard...'); // For debugging
            // Try multiple redirect methods
            try {
                window.location.href = 'dashboard.html';
            } catch (e) {
                console.error('Redirect failed:', e);
                // Fallback method
                window.location.replace('dashboard.html');
            }
        } else {
            alert('الرجاء إدخال اسم المستخدم وكلمة المرور');
        }
    });
} else {
    console.error('Login form not found!');
}
