// dashboard.js

let loadedDashboards = {
    hr: null,
    facilities: null
};

let currentDashboard = 'hr';

/**
 * ✨ NEW, ROBUST FUNCTION
 * Dynamically determines the correct base path for the site.
 * This is crucial for GitHub Pages project sites (e.g., user.github.io/repo-name/).
 * It ensures that no matter how the site is accessed, the path to our assets is correct.
 */
function getBasePath() {
    const path = window.location.pathname;
    // If path is '/repo-name/' or '/repo-name/index.html', etc., we extract '/repo-name'
    const repoName = path.split('/')[1];
    if (repoName && window.location.hostname.includes('github.io')) {
        return `/${repoName}`;
    }
    // For local development or a root domain, the base path is empty.
    return '';
}

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

    // ✨ CRITICAL CHANGE: Build the full, correct URL using the base path.
    const basePath = getBasePath();
    const hrDashboardUrl = `${basePath}/login/hr_dashboard.html?cache_bust=${new Date().getTime()}`;
    const facilitiesDashboardUrl = `${basePath}/login/facilities_dashboard.html?cache_bust=${new Date().getTime()}`;

    console.log("Attempting to fetch HR dashboard from:", hrDashboardUrl);
    console.log("Attempting to fetch Facilities dashboard from:", facilitiesDashboardUrl);

    Promise.all([
        fetch(hrDashboardUrl).then(res => {
            if (!res.ok) {
                console.error(`Failed to fetch ${hrDashboardUrl}. Status: ${res.status} ${res.statusText}`);
                return null;
            }
            return res.text();
        }),
        fetch(facilitiesDashboardUrl).then(res => {
            if (!res.ok) {
                console.error(`Failed to fetch ${facilitiesDashboardUrl}. Status: ${res.status} ${res.statusText}`);
                return null;
            }
            return res.text();
        })
    ]).then(([hrHtml, facilitiesHtml]) => {
        if (hrHtml) {
            loadedDashboards.hr = hrHtml;
            console.log('✅ HR Dashboard loaded successfully.');
        }
        if (facilitiesHtml) {
            loadedDashboards.facilities = facilitiesHtml;
            console.log('✅ Facilities Dashboard loaded successfully.');
        }
        
        document.getElementById('loading').style.display = 'none';
        if (!document.getElementById('iframe-container')) {
            document.getElementById('dashboard-content').innerHTML = '<div id="iframe-container" style="height: 100%;"><iframe id="dashboard-iframe" frameborder="0" style="width: 100%; height: 100%;"></iframe></div>';
        }
        document.getElementById('dashboard-content').style.display = 'block';

        displayDashboard(currentDashboard);

    }).catch(error => {
        console.error('CRITICAL ERROR during fetch operation:', error);
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
        showNoDataMessage("حدث خطأ في الشبكة أثناء محاولة تحميل التقارير.");
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
        updateDateFieldsFromHtml(dashboardHtml);
    } else {
        if (iframe) iframe.srcdoc = ''; // Clear iframe content
        const reportName = type === 'hr' ? 'الموارد البشرية' : 'إدارة المرافق';
        // This is the message you are seeing
        showNoDataMessage(`لم يتم العثور على تقرير ${reportName}. قد يكون قيد الإنشاء أو حدث خطأ.`);
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

function applyDateFilter() {
    alert("لا يمكن تغيير نطاق التواريخ يدوياً. يتم تحديث هذا التقرير تلقائياً. سيتم الآن جلب أحدث تقرير متاح.");
    refreshDashboard();
}

function refreshDashboard() {
    alert('جاري تحديث التقارير لأحدث نسخة متاحة...');
    loadAndDisplayInitialDashboard();
}

function showNoDataMessage(message) {
    const container = document.getElementById('dashboard-content');
    container.innerHTML = `<div class="no-data" style="height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 20px;">
                             <div style="font-size: 3rem; color: #FF8C00; margin-bottom: 1rem; background-color: #ffe8cc; width: 80px; height: 80px; border-radius: 50%; display: grid; place-items: center;">!</div>
                             <p style="font-size: 1.2rem; font-weight: 600;">${message}</p>
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
        window.location.href = 'index.html';
    }
}
