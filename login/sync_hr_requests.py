# login/sync_hr_requests.py

# --- Import Core Libraries ---
# Note: The 'pip install' command has been removed. It belongs in the workflow file.
import requests
import sys
import re
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
from google.auth import default

# --- AUTHENTICATION ---
# This script assumes authentication is handled by the environment (e.g., GitHub Actions).
try:
    creds, _ = default(scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
    gc = gspread.authorize(creds)
    print("✅ Service account authentication successful for HR Requests sync.")
except Exception as e:
    sys.exit(f"❌ ERROR: Google Authentication failed. Ensure credentials are set up correctly. Details: {e}")

# — CONFIGURATION —
API_KEY              = "8051c8104fd221694d9aeb305f7f4abb"
TEMPLATE_ID          = 994672 # HR Requests Form ID

# --- GOOGLE SHEETS CONFIGURATION ---
GOOGLE_SHEET_ID      = "1gYBXyTRT1J8uC9dz2t5pg4RHucapLS-_iLrDrWg17dY"
HR_SHEET_NAME        = "HR Requests Report"

# — MAPPING CONFIGURATION —
RAW_BRANCH_MAPPING_DATA = """
2197299 "LBRUH   B07"
2239240 FYJED  B32
2235670 "ANRUH   B31"
2190657 "SLAHS   B23"
2164026 "NDRUH   B15"
2164019 "SWRUH   B08"
2203271 "SARUH   B27"
2164017 "DARUH   B06"
2164032 "KRRUH   B21"
2164031 "SFJED   B24"
2164025 "RBRUH   B14"
2164016 RWRUH B05
2197297 "NSRUH   B04"
2164021 "SHRUH   B10"
2164013 "KHRUH   B02"
2155652 "NURUH   B01"
2164023 "TWRUH   B12"
2164020 "AZRUH   B09"
2199002 "RWAHS   B25"
2242934 "HIRJED      B33"
2164022 "NRRUH   B11"
2164030 "MURUH   B19"
2164014 "GHRUH   B03"
2211854 QARUH B30
2254072 Garatiss QB03
2256386 Garatiss QB04
2258220 PSJED   B36
2169459 "Lubda  Alaqeq Branch    LB01"
2232755 Garatis As Suwaidi - قراطيس السويدي   QB01
2185452 "OBJED   B22"
2243963 URRUH B34
2222802 "Lubda Alkhaleej Branch      LB02"
2199835 "HAJED   B26"
2210205 "MAJED   B28"
2250799 IRRUH B35
2164027 "BDRUH   B16"
2155654 "AQRUH   B13"
2197298 "TKRUH   B18"
2239240 "FAYJED      B32"
2250799 IRRUH35
2211854 "QADRUH      B30"
2243963 "URURUH      B34"
2239240 "FAYJED      B32"
2164017 Aldaraiah - الدرعية
2203271 Alsaadah branch - فرع السعادة
2155654 Al Aqeeq - العقيق
2164032 Alkharj - الخرج
2190657 Al Sulimaniyah Al Hofuf - السلمانية الهفوف
2211854 Al Qadisiyyah branch - فرع القادسية
2164013 Alkaleej - الخليج
2164027 Albadeah - البديعة
2171883 Twesste - تويستي TW01
2235805 Garatis Alnargis -  قراطيس النرجس  QB02
2164016 "RAWRUH      B05"
2164028 "QRRUH B17"
"""

def create_branch_map_prioritized(raw_data):
    """Creates a mapping from branch code to branch name."""
    branch_map = {}
    lines = raw_data.strip().split('\n')
    code_pattern = re.compile(r'\b[A-Z]{1,3}[0-9]{1,2}\b')
    for line in lines:
        line = line.strip()
        if not line: continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            code, branch_name = parts
            cleaned_name = ' '.join(branch_name.strip().strip('"').split())
            if code_pattern.search(cleaned_name):
                branch_map[code.strip()] = cleaned_name
    for line in lines:
        line = line.strip()
        if not line: continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            code, branch_name = parts
            code = code.strip()
            if code not in branch_map:
                cleaned_name = ' '.join(branch_name.strip().strip('"').split())
                branch_map[code] = cleaned_name
    return branch_map

BRANCH_MAP = create_branch_map_prioritized(RAW_BRANCH_MAPPING_DATA)

def zenput_headers():
    return {"X-API-TOKEN": API_KEY, "Content-Type": "application/json"}

def fetch_all_submissions(template_id):
    print(f"ℹ️ Fetching all submissions for template ID: {template_id}...")
    all_submissions = []
    start, limit = 0, 100
    while True:
        resp = requests.get(
            "https://www.zenput.com/api/v3/submissions/",
            headers=zenput_headers(),
            params={"form_template_id": template_id, "limit": limit, "start": start}
        )
        if resp.status_code != 200:
            sys.exit(f"❌ Error fetching submissions: HTTP {resp.status_code} - {resp.text}")
        batch = resp.json().get("data", [])
        if not batch:
            print(f"✅ Finished fetching. Found {len(all_submissions)} total submissions.")
            break
        all_submissions.extend(batch)
        print(f"   Fetched {len(all_submissions)} submissions so far...")
        start += limit
    return all_submissions

def process_hr_submissions_to_df(submissions):
    rows = []
    ZENPUT_FIELD_MAPPING = {
        'branch': 'Branch - الفرع',
        'request_type': 'Type of Request - نوع الطلب',
        'needs_name': 'Write name of needs - اكتب الإحتياج',
        'issue_description': 'Write the issue - اكتب المشكلة',
        'employee_info': '(اسم الموظف ورقمه الوظيفي (في حال الطلب متعلق بموظف',
        'priority': 'Priority - الأولوية',
        'request_status': 'Request Status - حالة الطلب',
        'comments': 'Comments - ملاحظات'
    }
    print("ℹ️ Processing HR submissions into a DataFrame...")
    for s in submissions:
        sm = s["smetadata"]
        answers = {ans["title"]: ans.get("value") for ans in s.get("answers", [])}
        raw_branch_code = str(answers.get(ZENPUT_FIELD_MAPPING['branch'], "")).strip()
        branch_name = BRANCH_MAP.get(raw_branch_code, raw_branch_code)
        submitted_by_name = sm.get("created_by", {}).get("display_name", "")
        submission_id = s.get('id')
        pdf_url = f"https://www.zenput.com/submission/{submission_id}/pdf/" if submission_id else ""
        row = {
            "Branch - الفرع": branch_name,
            "Submitted By": submitted_by_name,
            "Date Submitted": sm.get("date_submitted_local", ""),
            "Type of Request - نوع الطلب": answers.get(ZENPUT_FIELD_MAPPING['request_type']),
            "Write name of needs - اكتب الإحتياج": answers.get(ZENPUT_FIELD_MAPPING['needs_name']),
            "Write the issue - اكتب المشكلة": answers.get(ZENPUT_FIELD_MAPPING['issue_description']),
            "(اسم الموظف ورقمه الوظيفي (في حال الطلب متعلق بموظف": answers.get(ZENPUT_FIELD_MAPPING['employee_info']),
            "Priority - الأولوية": answers.get(ZENPUT_FIELD_MAPPING['priority']),
            "Request Status - حالة الطلب": answers.get(ZENPUT_FIELD_MAPPING['request_status']),
            "Comments - ملاحظات": answers.get(ZENPUT_FIELD_MAPPING['comments']),
            "pdf_link": pdf_url
        }
        rows.append(row)
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    def clean_value(value):
        if isinstance(value, list): return ', '.join(str(v).strip() for v in value if str(v).strip())
        elif pd.isna(value): return ""
        return str(value).strip()
    for col in df.columns:
        df[col] = df[col].apply(clean_value)
    df['Date Submitted'] = pd.to_datetime(df['Date Submitted'], errors='coerce').dt.strftime('%Y-%m-%d')
    status_col = "Request Status - حالة الطلب"
    default_status = "Pending - قيد الانتظار"
    df[status_col] = df[status_col].replace('', np.nan).fillna(default_status)
    critical_cols = ["Branch - الفرع", "Type of Request - نوع الطلب", "Write name of needs - اكتب الإحتياج", "Write the issue - اكتب المشكلة"]
    df.dropna(subset=critical_cols, how='all', inplace=True)
    df = df.loc[~(df[critical_cols].replace(r'^\s*$', '', regex=True) == '').all(axis=1)].copy()
    print("✅ DataFrame processing complete.")
    return df

def write_to_google_sheet(df, gc_client):
    print(f"ℹ️ Opening Google Sheet file by ID: {GOOGLE_SHEET_ID}")
    try:
        spreadsheet = gc_client.open_by_key(GOOGLE_SHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ ERROR: Spreadsheet not found. Make sure the ID '{GOOGLE_SHEET_ID}' is correct and you have shared the sheet.")
        return
    try:
        worksheet = spreadsheet.worksheet(HR_SHEET_NAME)
        print(f"ℹ️ Found existing sheet named '{HR_SHEET_NAME}'.")
    except gspread.exceptions.WorksheetNotFound:
        print(f"⚠️ Sheet '{HR_SHEET_NAME}' not found. Creating a new one...")
        worksheet = spreadsheet.add_worksheet(title=HR_SHEET_NAME, rows=1, cols=1)
    df_for_gsheet = df.fillna('')
    num_rows, num_cols = df_for_gsheet.shape
    print(f"ℹ️ Clearing old data and writing {len(df_for_gsheet)} new rows...")
    worksheet.clear()
    set_with_dataframe(worksheet, df_for_gsheet, row=1, col=1, include_index=False, include_column_header=True)
    worksheet.resize(rows=max(num_rows + 1, 2), cols=num_cols if num_cols > 0 else 1)
    if num_rows > 0:
        requests_batch = [
            {"clearBasicFilter": {"sheetId": worksheet.id}},
            {"setBasicFilter": {"filter": {"range": {
                "sheetId": worksheet.id, "startRowIndex": 0, "endRowIndex": num_rows + 1,
                "startColumnIndex": 0, "endColumnIndex": num_cols
            }}}},
            {"autoResizeDimensions": {"dimensions": {
                "sheetId": worksheet.id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": num_cols
            }}}
        ]
        spreadsheet.batch_update({"requests": requests_batch})
    print(f"✅ Success! The sheet '{HR_SHEET_NAME}' has been updated and formatted.")

# --- Main Execution Flow ---
if __name__ == "__main__":
    print("\n--- Starting HR Requests Form Sync ---")
    submissions = fetch_all_submissions(TEMPLATE_ID)
    if not submissions:
        print("ℹ️ No submissions were found for this HR form.")
    else:
        df_hr = process_hr_submissions_to_df(submissions)
        if df_hr.empty:
            print("ℹ️ DataFrame is empty after processing. No data will be written.")
        else:
            write_to_google_sheet(df_hr, gc)
    print("--- Script Finished ---\n")
