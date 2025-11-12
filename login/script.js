// Function to toggle password visibility
function togglePasswordVisibility() {
    const passwordField = document.getElementById('password');
    const toggleButton = document.getElementById('toggle-password');

    toggleButton.addEventListener('click', function() {
        const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordField.setAttribute('type', type);
        this.textContent = type === 'password' ? 'Show' : 'Hide';
    });
}

// Function to handle form submission
function handleFormSubmission(event) {
    event.preventDefault(); // Prevent the default form submit
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    // Example of handling form data
    console.log('Username:', username);
    console.log('Password:', password);
    // Add more processing logic as needed...
}

// Function to enable smooth animations
function smoothAnimations() {
    const form = document.getElementById('login-form');
    form.classList.add('fade-in'); // Add a class for animations
}

// Initialization
document.addEventListener('DOMContentLoaded', function() {
    togglePasswordVisibility();
    const form = document.getElementById('login-form');
    form.addEventListener('submit', handleFormSubmission);
    smoothAnimations();
});