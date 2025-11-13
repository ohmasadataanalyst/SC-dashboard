# --- THIS IS THE FINAL SCRIPT WITH ALL LOGIC CORRECTED ---

# Install and Authenticate first
!pip install requests pytz pandas gspread gspread-dataframe google-auth-oauthlib numpy openpyxl
from google.colab import auth
import gspread
from google.auth import default
auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)
print("✅ Authentication successful!")

# Import Core Libraries
import requests, sys, re, pandas as pd
from gspread_dataframe import set_with_dataframe

# — REPORT-SPECIFIC CONFIGURATION —
API_KEY              = "8051c8104fd221694d9aeb305f7f4abb"
HR_REPORT_NAME       = "HR Accommodation Visit"
HR_TEMPLATE_ID       = 672720
HR_GOOGLE_SHEET_ID   = "1gYBXyTRT1J8uC9dz2t5pg4RHucapLS-_iLrDrWg17dY"
HR_WORKSHEET_NAME    = "HR Accommodation Data"

# Field mapping for answers inside the form
HR_FIELD_MAPPING = {
    'location': 'Location',
    'problem_description': 'قم بكتابة توضيح للمشكلة',
}

# Definition for the final columns in the Google Sheet
HR_COLUMN_DEFINITIONS = {
    "Branch - الفرع": "location",
    "Date Submitted": "date_submitted",
    "Submitted By": "prepared_by",
    "Problem Description": "problem_description"
}

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
2175245 Albawasiq factory
2230615 Centeral Kitchen - المطبخ المركزي
"""

# --- HELPER FUNCTIONS ---

### --- THIS IS THE ORIGINAL, WORKING FUNCTION. I HAVE RESTORED IT. --- ###
def create_branch_map_prioritized(raw_data):
    branch_map = {}
    lines = raw_data.strip().split('\n')
    code_pattern = re.compile(r'\b[A-Z]{1,3}[0-9]{1,2}\b')
    # First pass: Prioritize entries that have a clear branch code in the name
    for line in lines:
        line = line.strip();
        if not line: continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            code, branch_name = parts
            cleaned_name = ' '.join(branch_name.strip().strip('"').split())
            if code_pattern.search(cleaned_name):
                branch_map[code.strip()] = cleaned_name
    # Second pass: Fill in the rest
    for line in lines:
        line = line.strip();
        if not line: continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            code, branch_name = parts; code = code.strip()
            if code not in branch_map:
                cleaned_name = ' '.join(branch_name.strip().strip('"').split())
                branch_map[code] = cleaned_name
    return branch_map

BRANCH_MAP = create_branch_map_prioritized(RAW_BRANCH_MAPPING_DATA)

def zenput_headers():
    return {"X-API-TOKEN": API_KEY, "Content-Type": "application/json"}

def fetch_all_submissions(template_id, form_name):
    print(f"ℹ️ Fetching all submissions for '{form_name}' (Template ID: {template_id})...")
    all_submissions = []; start, limit = 0, 100
    while True:
        resp = requests.get("https://www.zenput.com/api/v3/submissions/", headers=zenput_headers(), params={"form_template_id": template_id, "limit": limit, "start": start})
        if resp.status_code != 200: sys.exit(f"❌ Error fetching submissions: HTTP {resp.status_code} - {resp.text}")
        batch = resp.json().get("data", [])
        if not batch: print(f"✅ Finished fetching. Found {len(all_submissions)} total submissions."); break
        all_submissions.extend(batch); print(f"   Fetched {len(all_submissions)} submissions so far..."); start += limit
    return all_submissions

def process_submissions_to_df(submissions, field_mapping, column_definitions):
    rows = []
    print("ℹ️ Processing submissions into a DataFrame...")
    for s in submissions:
        sm = s["smetadata"]
        answers = {ans["title"]: ans.get("value") for ans in s.get("answers", [])}

        # Get location CODE from the form answer titled "Location"
        raw_location_code = str(answers.get(field_mapping['location'], "")).strip()
        # Look up the code in our custom map.
        final_location_name = BRANCH_MAP.get(raw_location_code, raw_location_code)

        problem_description = answers.get(field_mapping['problem_description'], "")

        created_by_info = sm.get('created_by', {})
        submitter_name = created_by_info.get('display_name', '')

        date_submitted = sm.get("date_submitted_local", "")

        row = {
            "Branch - الفرع": final_location_name,
            "Date Submitted": date_submitted,
            "Submitted By": submitter_name,
            "Problem Description": problem_description
        }
        rows.append(row)

    if not rows: return pd.DataFrame()

    df = pd.DataFrame(rows, columns=column_definitions.keys())

    def clean_value(value):
        if isinstance(value, list): return ', '.join(str(v).strip() for v in value if str(v).strip())
        elif pd.isna(value): return ""
        return str(value).strip()

    for col in df.columns: df[col] = df[col].apply(clean_value)

    if "Date Submitted" in df.columns:
        df["Date Submitted"] = pd.to_datetime(df["Date Submitted"], errors='coerce').dt.strftime('%Y-%m-%d')

    critical_cols = ["Branch - الفرع", "Problem Description"]
    df = df.loc[~(df[critical_cols].replace(r'^\s*$', '', regex=True) == '').all(axis=1)].copy()

    print(f"✅ DataFrame processing complete with {len(df)} rows.")
    return df

def write_to_google_sheet(df, gc_client, spreadsheet_id, worksheet_name):
    print(f"ℹ️ Opening Google Sheet by ID: {spreadsheet_id}")
    try:
        spreadsheet = gc_client.open_by_key(spreadsheet_id)
    except gspread.exceptions.SpreadsheetNotFound: print(f"❌ ERROR: Spreadsheet not found. Make sure ID is correct and shared."); return
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        print(f"✅ Found existing worksheet: '{worksheet_name}'")
    except gspread.exceptions.WorksheetNotFound:
        print(f"⚠️ Worksheet '{worksheet_name}' not found. Creating it now..."); worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=20)
    df_for_gsheet = df.fillna(''); num_rows, num_cols = df_for_gsheet.shape
    print(f"ℹ️ Clearing and rewriting worksheet '{worksheet_name}'..."); worksheet.clear()
    try: spreadsheet.batch_update({"requests": [{"clearBasicFilter": {"sheetId": worksheet.id}}]})
    except Exception: pass
    set_with_dataframe(worksheet, df_for_gsheet, row=1, col=1, include_index=False, include_column_header=True)
    worksheet.resize(rows=num_rows + 1, cols=num_cols)
    spreadsheet.batch_update({"requests": [{"setBasicFilter": {"filter": {"range": {"sheetId": worksheet.id}}}}, {"autoResizeDimensions": {"dimensions": {"sheetId": worksheet.id, "dimension": "COLUMNS"}}}]})
    print(f"✅ Success! Worksheet '{worksheet_name}' has been updated with {len(df_for_gsheet)} rows.")

# ——————————————
# — MAIN FLOW —
# ——————————————

print(f"\n--- STARTING REPORT: {HR_REPORT_NAME} ---")
submissions = fetch_all_submissions(HR_TEMPLATE_ID, HR_REPORT_NAME)
if submissions:
    df = process_submissions_to_df(submissions, HR_FIELD_MAPPING, HR_COLUMN_DEFINITIONS)
    if not df.empty:
        write_to_google_sheet(df, gc, HR_GOOGLE_SHEET_ID, HR_WORKSHEET_NAME)
    else: print(f"ℹ️ DataFrame is empty after processing. Nothing to write.")
else: print(f"ℹ️ No submissions were found for {HR_REPORT_NAME}.")
print(f"--- FINISHED REPORT: {HR_REPORT_NAME} ---\n")
