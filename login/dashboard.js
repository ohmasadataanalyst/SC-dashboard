// Store loaded dashboards
let loadedDashboards = {
    hr: null,
    facilities: null
};

let currentDashboard = 'hr';

// Initialize and auto-load dashboards
document.addEventListener('DOMContentLoaded', function() {
    // Show loading
    document.getElementById('loading').style.display = 'flex';
    document.getElementById('dashboard-content').style.display = 'none';
    
    // Auto-load dashboards from GitHub repository
    Promise.all([
        fetch('hr_dashboard.html').then(r => r.ok ? r.text() : null),
        fetch('facilities_dashboard.html').then(r => r.ok ? r.text() : null)
    ]).then(([hrHtml, facilitiesHtml]) => {
        if (hrHtml) {
            loadedDashboards.hr = hrHtml;
            console.log('✅ HR Dashboard loaded');
        }
        if (facilitiesHtml) {
            loadedDashboards.facilities = facilitiesHtml;
            console.log('✅ Facilities Dashboard loaded');
        }
        
        // Hide loading and show content
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
        
        // Display the current dashboard
        if (loadedDashboards[currentDashboard]) {
            displayDashboard(currentDashboard);
        } else {
            showNoDataMessage();
        }
    }).catch(error => {
        console.error('Error loading dashboards:', error);
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
        showNoDataMessage();
    });

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

function showNoDataMessage() {
    const container = document.getElementById('iframe-container');
    container.innerHTML = '<div class="no-data"><i class="fas fa-exclamation-circle"></i><p>لا توجد بيانات متاحة حالياً</p><p>سيتم تحديث التقارير تلقائياً قريباً</p></div>';
    container.style.display = 'block';
}

function switchDashboard(type) {
    currentDashboard = type;
    
    // Update title
    const title = type === 'hr' ? 'لوحة الموارد البشرية' : 'لوحة إدارة المرافق';
    document.getElementById('dashboard-title').textContent = title;
    
    // Show loaded dashboard if exists
    if (loadedDashboards[type]) {
        displayDashboard(type);
    } else {
        showNoDataMessage();
    }
}

function displayDashboard(type) {
    const iframe = document.getElementById('dashboard-iframe');
    const container = document.getElementById('iframe-container');
    
    if (loadedDashboards[type]) {
        // Clear any previous no-data message
        container.innerHTML = '<iframe id="dashboard-iframe" frameborder="0"></iframe>';
        const newIframe = document.getElementById('dashboard-iframe');
        newIframe.srcdoc = loadedDashboards[type];
        container.style.display = 'block';
    } else {
        showNoDataMessage();
    }
}

function downloadDashboard() {
    if (!loadedDashboards[currentDashboard]) {
        alert('الرجاء الانتظار حتى يتم تحميل التقرير');
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
    // Reload the dashboards from server
    document.getElementById('loading').style.display = 'flex';
    document.getElementById('dashboard-content').style.display = 'none';
    
    Promise.all([
        fetch('hr_dashboard.html?t=' + new Date().getTime()).then(r => r.ok ? r.text() : null),
        fetch('facilities_dashboard.html?t=' + new Date().getTime()).then(r => r.ok ? r.text() : null)
    ]).then(([hrHtml, facilitiesHtml]) => {
        if (hrHtml) loadedDashboards.hr = hrHtml;
        if (facilitiesHtml) loadedDashboards.facilities = facilitiesHtml;
        
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
        
        displayDashboard(currentDashboard);
        alert('✅ تم تحديث التقارير بنجاح');
    }).catch(error => {
        console.error('Error refreshing:', error);
        alert('❌ حدث خطأ أثناء التحديث');
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
    });
}

function logout() {
    if (confirm('هل تريد تسجيل الخروج؟')) {
        window.location.href = 'index.html';
    }
}
