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
    
    // Add your login logic here
    console.log('Username:', username);
    console.log('Password:', password);
    
    alert('Login submitted for user: ' + username);
});
