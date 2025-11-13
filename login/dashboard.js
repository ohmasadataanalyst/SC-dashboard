// dashboard.js

let loadedDashboards = {
    hr: null,
    facilities: null
};

let currentDashboard = 'hr';

document.addEventListener('DOMContentLoaded', function() {
    loadAndDisplayInitialDashboard();

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

function loadAndDisplayInitialDashboard() {
    document.getElementById('loading').style.display = 'flex';
    document.getElementById('dashboard-content').style.display = 'none';

    // ✨ CRITICAL CHANGE: The fetch paths now correctly point to the /login/ directory.
    const hrDashboardUrl = 'login/hr_dashboard.html?cache_bust=' + new Date().getTime();
    const facilitiesDashboardUrl = 'login/facilities_dashboard.html?cache_bust=' + new Date().getTime();

    Promise.all([
        fetch(hrDashboardUrl).then(res => res.ok ? res.text() : null),
        fetch(facilitiesDashboardUrl).then(res => res.ok ? res.text() : null)
    ]).then(([hrHtml, facilitiesHtml]) => {
        if (hrHtml) {
            loadedDashboards.hr = hrHtml;
            console.log('✅ HR Dashboard loaded from /login/');
        } else {
             console.error('❌ Failed to load HR Dashboard. Check if the file exists at: ' + hrDashboardUrl);
        }
        if (facilitiesHtml) {
            loadedDashboards.facilities = facilitiesHtml;
            console.log('✅ Facilities Dashboard loaded from /login/');
        } else {
            console.error('❌ Failed to load Facilities Dashboard. Check if the file exists at: ' + facilitiesDashboardUrl);
        }
        
        document.getElementById('loading').style.display = 'none';
        // Ensure the iframe container exists before trying to display the dashboard
        if (!document.getElementById('iframe-container')) {
            document.getElementById('dashboard-content').innerHTML = '<div id="iframe-container" style="height: 100%;"><iframe id="dashboard-iframe" frameborder="0" style="width: 100%; height: 100%;"></iframe></div>';
        }
        document.getElementById('dashboard-content').style.display = 'block';

        displayDashboard(currentDashboard);

    }).catch(error => {
        console.error('Error loading initial dashboards:', error);
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
        showNoDataMessage("فشل تحميل التقارير الأولية. تأكد من اتصالك بالإنترنت وحاول مرة أخرى.");
    });
}

function switchDashboard(type) {
    currentDashboard = type;
    const title = type === 'hr' ? 'لوحة الموارد البشرية' : 'لوحة إدارة المرافق';
    document.getElementById('dashboard-title').textContent = title;
    displayDashboard(type);
}

function displayDashboard(type) {
    const dashboardHtml = loadedDashboards[type];
    const iframe = document.getElementById('dashboard-iframe');

    if (iframe && dashboardHtml) {
        iframe.srcdoc = dashboardHtml;
        // Parse the HTML to find and set the dates in the filter fields
        updateDateFieldsFromHtml(dashboardHtml);
    } else {
        if (iframe) iframe.srcdoc = ''; // Clear iframe content
        const reportName = type === 'hr' ? 'الموارد البشرية' : 'إدارة المرافق';
        showNoDataMessage(`لم يتم العثور على تقرير ${reportName}. قد يكون قيد الإنشاء أو حدث خطأ.`);
        // Clear date fields if no dashboard is loaded
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
    }
}

// Reads dates from the dashboard HTML meta tags and updates the input fields
function updateDateFieldsFromHtml(htmlString) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlString, 'text/html');
    const startDate = doc.querySelector('meta[name="report-start-date"]')?.getAttribute('content');
    const endDate = doc.querySelector('meta[name="report-end-date"]')?.getAttribute('content');

    if (startDate && endDate) {
        document.getElementById('start-date').value = startDate;
        document.getElementById('end-date').value = endDate;
    }
}

// This function now explains its purpose and calls refreshDashboard
function applyDateFilter() {
    alert("لا يمكن تغيير نطاق التواريخ يدوياً. يتم تحديث هذا التقرير تلقائياً. سيتم الآن جلب أحدث تقرير متاح.");
    refreshDashboard();
}

function refreshDashboard() {
    alert('جاري تحديث التقارير لأحدث نسخة متاحة...');
    loadAndDisplayInitialDashboard(); // Re-run the initial load function
}

function showNoDataMessage(message) {
    const container = document.getElementById('dashboard-content');
    container.innerHTML = `<div class="no-data" style="height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                             <i class="fas fa-exclamation-circle" style="font-size: 3rem; color: #FF8C00; margin-bottom: 1rem;"></i>
                             <p>${message}</p>
                           </div>`;
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

function logout() {
    if (confirm('هل تريد تسجيل الخروج؟')) {
        // Assuming index.html is at the root
        window.location.href = 'index.html';
    }
}
