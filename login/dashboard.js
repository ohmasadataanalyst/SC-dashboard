// Store loaded dashboards
let loadedDashboards = {
    hr: null,
    facilities: null
};

let currentDashboard = 'hr';

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
    }, 1000);

    // Setup navigation
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
            
            const dashboard = this.getAttribute('data-dashboard');
            switchDashboard(dashboard);
        });
    });
});

function switchDashboard(type) {
    currentDashboard = type;
    
    // Update title
    const title = type === 'hr' ? 'لوحة الموارد البشرية' : 'لوحة إدارة المرافق';
    document.getElementById('dashboard-title').textContent = title;
    
    // Show loaded dashboard if exists
    if (loadedDashboards[type]) {
        displayDashboard(type);
    } else {
        document.getElementById('iframe-container').style.display = 'none';
    }
}

function loadDashboard(type, input) {
    const file = input.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        loadedDashboards[type] = e.target.result;
        
        if (currentDashboard === type) {
            displayDashboard(type);
        }
        
        // Show success message
        alert(`تم تحميل تقرير ${type === 'hr' ? 'الموارد البشرية' : 'المرافق'} بنجاح`);
    };
    reader.readAsText(file);
}

function displayDashboard(type) {
    const iframe = document.getElementById('dashboard-iframe');
    const container = document.getElementById('iframe-container');
    
    if (loadedDashboards[type]) {
        iframe.srcdoc = loadedDashboards[type];
        container.style.display = 'block';
    }
}

function downloadDashboard() {
    if (!loadedDashboards[currentDashboard]) {
        alert('الرجاء تحميل التقرير أولاً');
        return;
    }
    
    const blob = new Blob([loadedDashboards[currentDashboard]], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentDashboard}_report_${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function refreshDashboard() {
    const iframe = document.getElementById('dashboard-iframe');
    if (loadedDashboards[currentDashboard]) {
        iframe.srcdoc = loadedDashboards[currentDashboard];
        alert('تم تحديث اللوحة');
    } else {
        alert('لا يوجد تقرير محمل للتحديث');
    }
}

function logout() {
    if (confirm('هل تريد تسجيل الخروج؟')) {
        window.location.href = 'index.html';
    }
}
