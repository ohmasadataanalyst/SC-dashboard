// Password toggle functionality
const toggleBtn = document.getElementById('toggleBtn');
const passwordInput = document.getElementById('password');
const toggleText = document.getElementById('toggle-text');

toggleBtn.addEventListener('click', function() {
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleText.textContent = 'HIDE';
    } else {
        passwordInput.type = 'password';
        toggleText.textContent = 'SHOW';
    }
});

// Form submission
const loginForm = document.getElementById('loginForm');

loginForm.addEventListener('submit', function(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    // Add your login validation here
    if (username && password) {
        // Redirect to dashboard page
        window.location.href = 'dashboard.html';
    } else {
        alert('Please enter username and password');
    }
});
