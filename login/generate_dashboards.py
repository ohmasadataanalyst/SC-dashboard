#!/usr/bin/env python3
"""
Dashboard Generator for GitHub Actions
Automatically generates HR and Facilities dashboards from Google Sheets
"""

import pandas as pd
from datetime import datetime, timedelta
import json
import gspread
from google.oauth2.service_account import Credentials
import asyncio
import os
from pyppeteer import launch
import nest_asyncio

nest_asyncio.apply()

# Configuration
SHEET_KEY = '1gYBXyTRT1J8uC9dz2t5pg4RHucapLS-_iLrDrWg17dY'
MAIN_DATA_GID = 560668325
ACCOMMODATION_TAB_NAME = 'HR Accommodation Data'
FACILITIES_TYPES = ['Accommodations - سكن العمال', 'Containers - حاويات']

# Auto-calculate date range (last 7 days)
end_date = datetime.now()
start_date = end_date - timedelta(days=7)
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')

print(f"Generating reports from {start_date_str} to {end_date_str}")


async def create_html_and_pdf(html_content, html_filename, pdf_filename):
    """Saves the HTML file and uses a headless browser to convert it to a perfect PDF."""
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"✅ HTML report '{html_filename}' saved successfully.")

    print("🚀 Launching headless browser to create PDF...")
    browser = await launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
    page = await browser.newPage()
    await page.setViewport({'width': 2200, 'height': 1280})
    absolute_path = os.path.abspath(html_filename)
    await page.goto(f'file://{absolute_path}', {'waitUntil': 'networkidle0'})

    print(f"📄 Generating PDF '{pdf_filename}' (A3 Landscape)...")
    await page.pdf({
        'path': pdf_filename,
        'format': 'A3',
        'landscape': True,
        'printBackground': True,
        'margin': { 'top': '20px', 'right': '20px', 'bottom': '20px', 'left': '20px' }
    })
    await browser.close()
    print(f"✅ PDF '{pdf_filename}' created successfully.")


def generate_report(report_type, all_data, all_status_columns, start_date_str, end_date_str):
    """Generates a single, complete report (HTML and PDF) for a specific department."""
    print(f"\n{'='*60}\n--- Generating {report_type} Report for {start_date_str} to {end_date_str} ---\n{'='*60}")

    df = all_data['all_time']
    current_period_df = all_data['current']
    historical_df = all_data['historical']
    pending_from_before_df = all_data['pending']

    # 1. CALCULATE KPIs
    kpis = {
        'current_total': len(current_period_df),
        'current_completed': len(current_period_df[current_period_df['clean_status'] == 'Complete']),
        'current_incomplete': len(current_period_df[current_period_df['clean_status'] != 'Complete']),
        'current_critical_open': len(current_period_df[(current_period_df['clean_priority'] == 'High') & (current_period_df['clean_status'] != 'Complete')]),
        'all_time_total': len(df),
        'all_time_completed': len(df[df['clean_status'] == 'Complete']),
        'all_time_incomplete': len(df[df['clean_status'] != 'Complete']),
        'all_time_critical_open': len(df[(df['clean_priority'] == 'High') & (df['clean_status'] != 'Complete')]),
    }
    request_complete_pct_current = (kpis['current_completed'] / kpis['current_total'] * 100) if kpis['current_total'] > 0 else 0
    request_complete_pct_all_time = (kpis['all_time_completed'] / kpis['all_time_total'] * 100) if kpis['all_time_total'] > 0 else 0

    if report_type == 'Facilities':
        start_date_dt, end_date_dt = datetime.strptime(start_date_str, '%Y-%m-%d'), datetime.strptime(end_date_str, '%Y-%m-%d')
        num_days_current = (end_date_dt - start_date_dt).days + 1
        target_visits_current = num_days_current * 4
        actual_visits_current = len(all_data['current_accommodation'])
        visit_achieve_pct_current = (actual_visits_current / target_visits_current * 100) if target_visits_current > 0 else 0
        kpis['department_performance_rate_current'] = (visit_achieve_pct_current + request_complete_pct_current) / 2
        kpis['department_performance_rate_all_time'] = request_complete_pct_all_time
    else:
        kpis['department_performance_rate_current'] = request_complete_pct_current
        kpis['department_performance_rate_all_time'] = request_complete_pct_all_time

    def generate_request_type_table_html(df, all_possible_statuses):
        if df.empty: return f'<tr><td colspan="{len(all_possible_statuses) + 2}">No requests in this period.</td></tr>'
        perf = df.groupby('type')['status'].value_counts().unstack(fill_value=0).reindex(columns=all_possible_statuses, fill_value=0)
        perf['Total'] = perf.sum(axis=1)
        all_cols_in_order = ['Total'] + all_possible_statuses
        perf = perf[all_cols_in_order]
        rows = []
        for req_type, row in perf.iterrows():
            row_html = f"<tr><td>{req_type}</td>"
            for col_name in all_cols_in_order:
                value = row.get(col_name, 0)
                if col_name == 'Total': row_html += f"<td>{value}</td>"
                else:
                    percentage = (value / row['Total'] * 100) if row['Total'] > 0 else 0
                    row_html += f"<td>{value} ({percentage:.0f}%)</td>"
            rows.append(row_html + "</tr>")
        return "".join(rows)

    status_headers_html = "".join([f"<th>{header}</th>" for header in ['الإجمالي'] + all_status_columns])
    current_req_type_html = generate_request_type_table_html(current_period_df, all_status_columns)
    previous_req_type_html = generate_request_type_table_html(historical_df, all_status_columns)

    def generate_detailed_rows(df):
        if df.empty: return '<tr><td colspan="9">No data to display.</td></tr>'
        rows = []
        for _, row in df.iterrows():
            row_class = 'highlight-critical' if row['clean_priority'] == 'High' and row['clean_status'] != 'Complete' else ''
            rows.append(f"""<tr class="{row_class}"><td>{row.get('branch', '')}</td><td>{row.get('submitted_by', '')}</td><td>{row.get('employee_details', '')}</td><td>{row.get('type', '')}</td><td>{row.get('item', '')}</td><td>{row.get('issue', '')}</td><td>{row.get('priority', '')}</td><td>{row.get('status', '')}</td><td>{row.get('comments', '')}</td></tr>""")
        return "".join(rows)
    
    current_period_rows = generate_detailed_rows(current_period_df)
    pending_from_before_rows = generate_detailed_rows(pending_from_before_df)

    def prepare_chart_data(df):
        charts = {}
        if df.empty:
            empty_chart = {"labels": [], "datasets": []}
            return {key: json.dumps(empty_chart) for key in ['type_chart', 'status_chart', 'priority_chart', 'branch_chart']}
        type_stats = df.groupby('type')['clean_status'].value_counts().unstack(fill_value=0)
        type_stats['incomplete'] = type_stats.drop('Complete', axis=1, errors='ignore').sum(axis=1)
        type_stats['complete'] = type_stats.get('Complete', 0)
        charts['type_chart'] = {"labels": type_stats.index.tolist(), "datasets": [ {"label": "مكتملة", "data": type_stats['complete'].tolist(), "backgroundColor": '#28a745'}, {"label": "غير مكتملة", "data": type_stats['incomplete'].tolist(), "backgroundColor": '#dc3545'} ]}
        status_counts = df['status'].value_counts()
        charts['status_chart'] = {"labels": status_counts.index.tolist(), "datasets": [{"data": status_counts.values.tolist(), "backgroundColor": ['#ffc107', '#28a745', '#007bff', '#6f42c1', '#6c757d', '#fd7e14']}]}
        priority_counts = df['priority'].value_counts()
        charts['priority_chart'] = {"labels": priority_counts.index.tolist(), "datasets": [{"data": priority_counts.values.tolist(), "backgroundColor": ['#dc3545', '#fd7e14', '#28a745', '#007bff']}]}
        branch_counts = df['branch'].value_counts().nlargest(10)
        charts['branch_chart'] = {"labels": branch_counts.index.tolist(), "datasets": [{"label": "الطلبات", "data": branch_counts.values.tolist(), "backgroundColor": '#4DB6AC', "borderRadius": 4}]}
        return {key: json.dumps(value, ensure_ascii=False) for key, value in charts.items()}

    current_chart_data = prepare_chart_data(current_period_df)
    all_time_chart_data = prepare_chart_data(df)

    render_context = {
        'kpis': kpis,
        'current_chart_data': current_chart_data,
        'all_time_chart_data': all_time_chart_data,
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
        'current_period_rows': current_period_rows,
        'pending_from_before_rows': pending_from_before_rows
    }

    department_sections_html = f"""
    <section class="card"><h3>تحليل أنواع الطلبات (الفترة الحالية)</h3><div><table><thead><tr><th>نوع الطلب</th>{status_headers_html}</tr></thead><tbody>{current_req_type_html}</tbody></table></div></section>
    <section class="card"><h3>تحليل أنواع الطلبات (كل الفترات السابقة)</h3><div><table><thead><tr><th>نوع الطلب</th>{status_headers_html}</tr></thead><tbody>{previous_req_type_html}</tbody></table></div></section>
    """

    if report_type == 'Facilities':
        def generate_accommodation_table_html(df):
            if df.empty: return '<tr><td colspan="2">No accommodation data for this period.</td></tr>'
            return "".join([f"<tr><td>{officer}</td><td>{count}</td></tr>" for officer, count in df['hr_officer'].value_counts().items()])
        accommodation_table_html = generate_accommodation_table_html(all_data['current_accommodation'])
        facilities_specific_section = f"""<section class="card"><h3>تقارير سكن الموظفين (الفترة الحالية)</h3><div><table><thead><tr><th>المسؤول</th><th>عدد التقارير</th></tr></thead><tbody>{accommodation_table_html}</tbody></table></div></section>"""
        render_context['department_specific_sections'] = facilities_specific_section + department_sections_html
        render_context['report_title'] = f"تقرير إدارة المرافق للفترة من {start_date_str} إلى {end_date_str}"
        render_context['sidebar_icon'] = "fa-solid fa-building-user"
        render_context['sidebar_title'] = "تقرير المرافق"
        render_context['main_title'] = "لوحة متابعة أداء إدارة المرافق"
    else:
        render_context['department_specific_sections'] = department_sections_html
        render_context['report_title'] = f"تقرير الموارد البشرية للفترة من {start_date_str} إلى {end_date_str}"
        render_context['sidebar_icon'] = "fas fa-users"
        render_context['sidebar_title'] = "تقرير الموارد البشرية"
        render_context['main_title'] = "لوحة متابعة أداء الموارد البشرية"

    base_html = """<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>{report_title}</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0"></script><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.0/css/all.min.css"><link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet"><style>:root{{--primary-dark:#004D40;--primary-light:#00796B;--secondary:#4DB6AC;--background:#E0F2F1;--card-bg:#ffffff;--text-dark:#333;--text-light:#E0F2F1;--text-muted:#6c757d;--border-color:#B2DFDB;--color-green:#28a745;--color-red:#dc3545}}body{{font-family:'Cairo','Noto Naskh Arabic',sans-serif;direction:rtl;text-align:right;background-color:#E0F2F1!important;color:var(--text-dark);margin:0;print-color-adjust:exact;-webkit-print-color-adjust:exact}}.dashboard-container{{display:flex;width:100%;min-height:100vh}}.sidebar{{width:280px;background-color:var(--primary-dark);color:var(--text-light);padding:25px;display:flex;flex-direction:column;flex-shrink:0}}.main-content{{flex-grow:1;padding:30px;min-width:0}}.sidebar-header h1{{color:#fff;margin:0 0 5px 0;font-size:1.5rem}}.sidebar-header .logo{{font-size:1.8rem;margin-left:10px}}.sidebar h2{{font-size:1.1rem;margin:20px 0 15px 0;color:var(--text-light);border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:10px}}.kpi-grid-sidebar{{display:flex;flex-direction:column;gap:10px}}.kpi-card-sidebar{{background:var(--primary-light);padding:10px 15px;border-radius:8px;display:flex;align-items:center;gap:15px}}.kpi-card-sidebar .icon{{font-size:1.5rem;width:40px;height:40px;display:grid;place-items:center;border-radius:50%;background-color:rgba(0,0,0,0.1)}}.kpi-card-sidebar .text .value{{font-size:1.8rem;font-weight:700;color:#fff}}.kpi-card-sidebar .text .label{{font-size:0.85rem;opacity:0.8}}.kpi-card-sidebar.previous{{background-color:#6a737b}}.main-header .title-area h1{{font-size:2.2rem;margin:0 0 5px 0;color:var(--primary-dark)}}.main-header .title-area p{{font-size:1.2rem;color:var(--text-muted);margin:0}}.card{{background-color:var(--card-bg);padding:25px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.06);margin-bottom:25px}}.card h3{{margin:0 0 20px 0;font-size:1.4rem;color:var(--primary-dark);padding-bottom:10px;border-bottom:2px solid var(--border-color)}}.charts-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:25px}}.chart-container{{height:350px}}.chart-container-full{{height:400px}}table{{width:100%;border-collapse:collapse;table-layout:auto;word-break:break-word}}th,td{{padding:10px 8px;text-align:center;vertical-align:middle;border:1px solid #dee2e6}}th{{font-weight:600;background-color:#6c757d;color:white}}.detailed-table th,.detailed-table td{{border-bottom:1px solid var(--border-color);text-align:right;border-left:none;border-right:none}}.detailed-table th{{background-color:#f1f8f8;color:var(--text-dark)}}tbody tr:nth-child(even){{background-color:#f8f9fa}}tbody tr:hover{{background-color:#e8f5e9}}.highlight-critical{{background-color:#fff0f1!important;font-weight:bold}}</style></head><body><div class="dashboard-container"><aside class="sidebar"><div class="sidebar-header"><i class="{sidebar_icon} logo"></i><h1>{sidebar_title}</h1></div><h2>مؤشرات الفترة الحالية</h2><div class="kpi-grid-sidebar"><div class="kpi-card-sidebar"><div class="icon"><i class="fas fa-tachometer-alt"></i></div><div class="text"><p class="value">{kpis[department_performance_rate_current]:.1f}%</p><p class="label">معدل أداء الإدارة</p></div></div><div class="kpi-card-sidebar"><div class="icon"><i class="fas fa-list-ol"></i></div><div class="text"><p class="value">{kpis[current_total]}</p><p class="label">إجمالي الطلبات</p></div></div><div class="kpi-card-sidebar"><div class="icon"><i class="fas fa-check-circle"></i></div><div class="text"><p class="value">{kpis[current_completed]}</p><p class="label">مكتملة</p></div></div><div class="kpi-card-sidebar"><div class="icon"><i class="fas fa-hourglass-half"></i></div><div class="text"><p class="value">{kpis[current_incomplete]}</p><p class="label">غير مكتملة</p></div></div><div class="kpi-card-sidebar"><div class="icon"><i class="fas fa-triangle-exclamation"></i></div><div class="text"><p class="value">{kpis[current_critical_open]}</p><p class="label">حرجة ومفتوحة</p></div></div></div><h2>المؤشرات الإجمالية</h2><div class="kpi-grid-sidebar"><div class="kpi-card-sidebar previous"><div class="icon"><i class="fas fa-chart-line"></i></div><div class="text"><p class="value">{kpis[department_performance_rate_all_time]:.1f}%</p><p class="label">معدل الأداء الإجمالي</p></div></div><div class="kpi-card-sidebar previous"><div class="icon"><i class="fas fa-list-ol"></i></div><div class="text"><p class="value">{kpis[all_time_total]}</p><p class="label">إجمالي الطلبات</p></div></div></div></aside><main class="main-content"><header class="main-header"><div class="title-area"><h1>{main_title}</h1><p>للفترة من {start_date_str} إلى {end_date_str}</p></div></header>{department_specific_sections}<section class="card"><h3>التحليلات المرئية للطلبات (الفترة الحالية)</h3><div class="charts-grid"><div class="chart-container"><h3>حالة الطلبات</h3><canvas id="statusChart"></canvas></div><div class="chart-container"><h3>حسب الأولوية</h3><canvas id="priorityChart"></canvas></div><div class="chart-container"><h3>أكثر الفروع تقديماً للطلبات</h3><canvas id="branchChart"></canvas></div></div><div class="chart-container-full" style="margin-top:25px;"><h3>الطلبات حسب النوع</h3><canvas id="typeChart"></canvas></div></section><section class="card"><h3>التحليلات المرئية للطلبات (لكل الأوقات)</h3><div class="charts-grid"><div class="chart-container"><h3>حالة الطلبات</h3><canvas id="allTimeStatusChart"></canvas></div><div class="chart-container"><h3>حسب الأولوية</h3><canvas id="allTimePriorityChart"></canvas></div><div class="chart-container"><h3>أكثر الفروع تقديماً للطلبات</h3><canvas id="allTimeBranchChart"></canvas></div></div><div class="chart-container-full" style="margin-top:25px;"><h3>الطلبات حسب النوع</h3><canvas id="allTimeTypeChart"></canvas></div></section><section class="card"><h3>جدول الطلبات (الفترة الحالية)</h3><div><table class="detailed-table"><thead><tr><th>الفرع</th><th>مُقدم الطلب</th><th>بيانات الموظف</th><th>النوع</th><th>الإحتياج</th><th>المشكلة</th><th>الأولوية</th><th>الحالة</th><th>ملاحظات</th></tr></thead><tbody>{current_period_rows}</tbody></table></div></section><section class="card"><h3>الطلبات المعلقة من الفترات السابقة</h3><div><table class="detailed-table"><thead><tr><th>الفرع</th><th>مُقدم الطلب</th><th>بيانات الموظف</th><th>النوع</th><th>الإحتياج</th><th>المشكلة</th><th>الأولوية</th><th>الحالة</th><th>ملاحظات</th></tr></thead><tbody>{pending_from_before_rows}</tbody></table></div></section></main></div><script>document.addEventListener('DOMContentLoaded',function(){{Chart.register(ChartDataLabels);Chart.defaults.font.family="'Cairo','Noto Naskh Arabic',sans-serif";Chart.defaults.font.size=12;Chart.defaults.plugins.datalabels.font.weight='bold';Chart.defaults.maintainAspectRatio=false;Chart.defaults.animation=false;const pieDoughnutFormatter=(v,c)=>{{const d=c.chart.data.datasets[0].data;if(v===0)return'';if(d.length<=2){{const t=d.reduce((s,d)=>s+d,0);const p=(v/t*100);return`${{v}}\\n(${{p.toFixed(0)}}%)`}}const s=[...d].sort((a,b)=>b-a);if(v>=s[1]){{const t=d.reduce((s,d)=>s+d,0);const p=(v/t*100);return`${{v}}\\n(${{p.toFixed(0)}}%)`}}else return''}};const stackedBarFormatter=(v,c)=>{{if(v===0)return'';const t=c.chart.data.datasets.reduce((s,d)=>s+(d.data[c.dataIndex]||0),0);const p=(v/t*100);return`${{v}}\\n(${{p.toFixed(0)}}%)`}};const pieDoughnutOptions={{plugins:{{legend:{{position:'right'}},datalabels:{{anchor:'end',align:'end',offset:8,clamp:true,color:'black',font:{{size:11,weight:'600'}},formatter:pieDoughnutFormatter}}}},layout:{{padding:{{top:30,bottom:30,left:30,right:40}}}}}};const horizontalBarOptions={{indexAxis:'y',plugins:{{legend:{{display:false}},datalabels:{{anchor:'end',align:'end',offset:4,color:'black',font:{{weight:'600'}},formatter:(v)=>v}}}},scales:{{x:{{beginAtZero:true,grace:'10%'}}}},layout:{{padding:{{right:30}}}}}};const stackedBarOptions={{scales:{{x:{{stacked:true,ticks:{{maxRotation:65,minRotation:45,autoSkip:false}}}},y:{{stacked:true,beginAtZero:true}}}},plugins:{{legend:{{position:'top'}},tooltip:{{mode:'index'}},datalabels:{{anchor:'center',align:'center',color:'black',font:{{size:10}},formatter:stackedBarFormatter}}}}}};new Chart(document.getElementById('typeChart'),{{type:'bar',data:JSON.parse(`{current_chart_data[type_chart]}`),options:stackedBarOptions}});new Chart(document.getElementById('statusChart'),{{type:'doughnut',data:JSON.parse(`{current_chart_data[status_chart]}`),options:pieDoughnutOptions}});new Chart(document.getElementById('priorityChart'),{{type:'pie',data:JSON.parse(`{current_chart_data[priority_chart]}`),options:pieDoughnutOptions}});new Chart(document.getElementById('branchChart'),{{type:'bar',data:JSON.parse(`{current_chart_data[branch_chart]}`),options:horizontalBarOptions}});new Chart(document.getElementById('allTimeTypeChart'),{{type:'bar',data:JSON.parse(`{all_time_chart_data[type_chart]}`),options:stackedBarOptions}});new Chart(document.getElementById('allTimeStatusChart'),{{type:'doughnut',data:JSON.parse(`{all_time_chart_data[status_chart]}`),options:pieDoughnutOptions}});new Chart(document.getElementById('allTimePriorityChart'),{{type:'pie',data:JSON.parse(`{all_time_chart_data[priority_chart]}`),options:pieDoughnutOptions}});new Chart(document.getElementById('allTimeBranchChart'),{{type:'bar',data:JSON.parse(`{all_time_chart_data[branch_chart]}`),options:horizontalBarOptions}})}});</script></body></html>"""
    
    final_html = base_html.format(**render_context)

    base_filename = f"{report_type}_Report_{start_date_str}_to_{end_date_str}"
    html_filename = f"{base_filename}.html"
    pdf_filename = f"{base_filename}.pdf"

    asyncio.get_event_loop().run_until_complete(
        create_html_and_pdf(final_html, html_filename, pdf_filename)
    )
    return html_filename, pdf_filename


def run_all_reports(sheet_key, main_gid, accommodation_tab_name, start_date_str, end_date_str):
    """Main orchestrator: Fetches data, splits it by department, and generates a report for each."""
    try:
        print("Authenticating with Google Sheets...")
        
        # Use service account credentials for GitHub Actions
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        
        creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(sheet_key)

        main_worksheet = next(ws for ws in spreadsheet.worksheets() if ws.id == main_gid)
        df = pd.DataFrame(main_worksheet.get_all_records())
        
        hr_col_map = {
            'Branch - الفرع': 'branch',
            'Submitted By': 'submitted_by',
            'Date Submitted': 'date_submitted',
            'Type of Request - نوع الطلب': 'type',
            'Write name of needs - اكتب الإحتياج': 'item',
            'Write the issue - اكتب المشكلة': 'issue',
            '(اسم الموظف ورقمه الوظيفي (في حال الطلب متعلق بموظف': 'employee_details',
            'Priority - الأولوية': 'priority',
            'Request Status - حالة الطلب': 'status',
            'Comments - ملاحظات': 'comments',
            'pdf_link': 'pdf_link'
        }
        
        df.rename(columns=hr_col_map, inplace=True)
        df['status'] = df['status'].astype(str)
        df['date_submitted'] = pd.to_datetime(df['date_submitted'].replace('', pd.NaT), errors='coerce')
        df.dropna(subset=['date_submitted'], inplace=True)
        df['clean_status'] = df['status'].apply(lambda x: str(x).split(' - ')[0].strip())
        df['clean_priority'] = df['priority'].apply(lambda x: str(x).split(' - ')[0].strip())
        df['clean_type'] = df['type'].apply(lambda x: str(x).split(' - ')[0].strip())

        accommodation_worksheet = spreadsheet.worksheet(accommodation_tab_name)
        accommodation_df = pd.DataFrame(accommodation_worksheet.get_all_records())
        if not accommodation_df.empty:
            accommodation_df.rename(columns={'Date Submitted': 'entry_date', 'Submitted By': 'hr_officer', 'Location': 'location'}, inplace=True)
            accommodation_df['entry_date'] = pd.to_datetime(accommodation_df['entry_date'].replace('', pd.NaT), errors='coerce')
            accommodation_df.dropna(subset=['entry_date'], inplace=True)
        else:
            accommodation_df = pd.DataFrame(columns=['entry_date', 'hr_officer', 'location'])
        print("✅ Data fetching and cleaning complete.")
    except Exception as e:
        print(f"❌ An error occurred during data fetching: {e}")
        raise

    facilities_df = df[df['type'].isin(FACILITIES_TYPES)].copy()
    hr_df = df[~df['type'].isin(FACILITIES_TYPES)].copy()
    print(f"Data split: {len(hr_df)} HR requests, {len(facilities_df)} Facilities requests.")

    all_status_columns = sorted([s for s in df['status'].unique() if s and str(s).strip()])
    start_date_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date_dt = datetime.strptime(end_date_str, '%Y-%m-%d')

    hr_data = {
        'all_time': hr_df,
        'current': hr_df[(hr_df['date_submitted'] >= start_date_dt) & (hr_df['date_submitted'] <= end_date_dt)],
        'historical': hr_df[hr_df['date_submitted'] < start_date_dt],
        'pending': hr_df[(hr_df['date_submitted'] < start_date_dt) & (hr_df['clean_status'] != 'Complete')]
    }
    facilities_data = {
        'all_time': facilities_df,
        'current': facilities_df[(facilities_df['date_submitted'] >= start_date_dt) & (facilities_df['date_submitted'] <= end_date_dt)],
        'historical': facilities_df[facilities_df['date_submitted'] < start_date_dt],
        'pending': facilities_df[(facilities_df['date_submitted'] < start_date_dt) & (facilities_df['clean_status'] != 'Complete')],
        'current_accommodation': accommodation_df[(accommodation_df['entry_date'] >= start_date_dt) & (accommodation_df['entry_date'] <= end_date_dt)]
    }

    print("\n" + "="*60)
    print("Generating HR Dashboard...")
    print("="*60)
    hr_html, hr_pdf = generate_report('HR', hr_data, all_status_columns, start_date_str, end_date_str)
    
    print("\n" + "="*60)
    print("Generating Facilities Dashboard...")
    print("="*60)
    facilities_html, facilities_pdf = generate_report('Facilities', facilities_data, all_status_columns, start_date_str, end_date_str)

    print("\n" + "="*60)
    print("✅ ALL REPORTS GENERATED SUCCESSFULLY!")
    print("="*60)
    print(f"HR Report: {hr_html}")
    print(f"Facilities Report: {facilities_html}")
    
    return hr_html, facilities_html


if __name__ == "__main__":
    print("="*60)
    print("SC Dashboard Generator - GitHub Actions")
    print("="*60)
    
    # Check if credentials file exists
    if not os.path.exists('credentials.json'):
        print("❌ ERROR: credentials.json not found!")
        print("Make sure GOOGLE_CREDENTIALS secret is set in GitHub.")
        exit(1)
    
    try:
        run_all_reports(SHEET_KEY, MAIN_DATA_GID, ACCOMMODATION_TAB_NAME, start_date_str, end_date_str)
        print("\n" + "="*60)
        print("✅ SUCCESS! All dashboards generated.")
        print("="*60)
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ ERROR: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        exit(1)
