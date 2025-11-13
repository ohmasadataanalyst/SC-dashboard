#!/usr/bin/env python3
"""
Google Sheets Update Script
Updates HR Requests and HR Accommodation data from Zenput API
"""

import requests
import sys
import re
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

# Configuration
API_KEY = "8051c8104fd221694d9aeb305f7f4abb"
GOOGLE_SHEET_ID = "1gYBXyTRT1J8uC9dz2t5pg4RHucapLS-_iLrDrWg17dY"

# HR Requests Configuration
HR_REQUESTS_TEMPLATE_ID = 994672
HR_REQUESTS_SHEET_NAME = "HR Requests Report"

# HR Accommodation Configuration  
HR_ACCOMMODATION_TEMPLATE_ID = 672720
HR_ACCOMMODATION_SHEET_NAME = "HR Accommodation Data"

# Branch Mapping
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

def create_branch_map_prioritized(raw_data):
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

def fetch_all_submissions(template_id, form_name):
    print(f"ℹ️ Fetching submissions for '{form_name}' (ID: {template_id})...")
    all_submissions = []
    start, limit = 0, 100
    while True:
        resp = requests.get(
            "https://www.zenput.com/api/v3/submissions/",
            headers=zenput_headers(),
            params={"form_template_id": template_id, "limit": limit, "start": start}
        )
        if resp.status_code != 200:
            print(f"❌ Error: HTTP {resp.status_code}")
            break
        batch = resp.json().get("data", [])
        if not batch:
            break
        all_submissions.extend(batch)
        start += limit
    print(f"✅ Fetched {len(all_submissions)} submissions")
    return all_submissions

def process_hr_requests(submissions):
    rows = []
    for s in submissions:
        sm = s["smetadata"]
        answers = {ans["title"]: ans.get("value") for ans in s.get("answers", [])}
        raw_branch_code = str(answers.get('Branch - الفرع', "")).strip()
        branch_name = BRANCH_MAP.get(raw_branch_code, raw_branch_code)
        submitted_by_name = sm.get("created_by", {}).get("display_name", "")
        submission_id = s.get('id')
        pdf_url = f"https://www.zenput.com/submission/{submission_id}/pdf/" if submission_id else ""

        row = {
            "Branch - الفرع": branch_name,
            "Submitted By": submitted_by_name,
            "Date Submitted": sm.get("date_submitted_local", ""),
            "Type of Request - نوع الطلب": answers.get('Type of Request - نوع الطلب'),
            "Write name of needs - اكتب الإحتياج": answers.get('Write name of needs - اكتب الإحتياج'),
            "Write the issue - اكتب المشكلة": answers.get('Write the issue - اكتب المشكلة'),
            "(اسم الموظف ورقمه الوظيفي (في حال الطلب متعلق بموظف": answers.get('(اسم الموظف ورقمه الوظيفي (في حال الطلب متعلق بموظف'),
            "Priority - الأولوية": answers.get('Priority - الأولوية'),
            "Request Status - حالة الطلب": answers.get('Request Status - حالة الطلب'),
            "Comments - ملاحظات": answers.get('Comments - ملاحظات'),
            "pdf_link": pdf_url
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    
    def clean_value(value):
        if isinstance(value, list):
            return ', '.join(str(v).strip() for v in value if str(v).strip())
        elif pd.isna(value):
            return ""
        return str(value).strip()

    for col in df.columns:
        df[col] = df[col].apply(clean_value)

    df['Date Submitted'] = pd.to_datetime(df['Date Submitted'], errors='coerce').dt.strftime('%Y-%m-%d')
    status_col = "Request Status - حالة الطلب"
    default_status = "Pending - قيد الانتظار"
    df[status_col] = df[status_col].replace('', np.nan).fillna(default_status)

    return df

def process_hr_accommodation(submissions):
    rows = []
    for s in submissions:
        sm = s["smetadata"]
        answers = {ans["title"]: ans.get("value") for ans in s.get("answers", [])}
        raw_location_code = str(answers.get('Location', "")).strip()
        final_location_name = BRANCH_MAP.get(raw_location_code, raw_location_code)
        problem_description = answers.get('قم بكتابة توضيح للمشكلة', "")
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

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    
    def clean_value(value):
        if isinstance(value, list):
            return ', '.join(str(v).strip() for v in value if str(v).strip())
        elif pd.isna(value):
            return ""
        return str(value).strip()

    for col in df.columns:
        df[col] = df[col].apply(clean_value)

    df["Date Submitted"] = pd.to_datetime(df["Date Submitted"], errors='coerce').dt.strftime('%Y-%m-%d')
    
    return df

def write_to_google_sheet(df, gc_client, sheet_name):
    print(f"ℹ️ Writing to sheet: {sheet_name}")
    try:
        spreadsheet = gc_client.open_by_key(GOOGLE_SHEET_ID)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=20)
        
        df_for_gsheet = df.fillna('')
        num_rows, num_cols = df_for_gsheet.shape
        worksheet.clear()
        set_with_dataframe(worksheet, df_for_gsheet, row=1, col=1, include_index=False, include_column_header=True)
        
        requests_batch = [
            {"setBasicFilter": {"filter": {"range": {"sheetId": worksheet.id}}}},
            {"autoResizeDimensions": {"dimensions": {"sheetId": worksheet.id, "dimension": "COLUMNS"}}}
        ]
        spreadsheet.batch_update({"requests": requests_batch})
        print(f"✅ Updated {sheet_name} with {len(df)} rows")
    except Exception as e:
        print(f"❌ Error updating {sheet_name}: {e}")

def main():
    print("="*60)
    print("Google Sheets Update Script")
    print("="*60)
    
    # Authenticate
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    gc = gspread.authorize(creds)
    
    # Update HR Requests
    print("\n--- Updating HR Requests ---")
    hr_requests_submissions = fetch_all_submissions(HR_REQUESTS_TEMPLATE_ID, "HR Requests")
    if hr_requests_submissions:
        df_hr_requests = process_hr_requests(hr_requests_submissions)
        if not df_hr_requests.empty:
            write_to_google_sheet(df_hr_requests, gc, HR_REQUESTS_SHEET_NAME)
    
    # Update HR Accommodation
    print("\n--- Updating HR Accommodation ---")
    hr_accommodation_submissions = fetch_all_submissions(HR_ACCOMMODATION_TEMPLATE_ID, "HR Accommodation")
    if hr_accommodation_submissions:
        df_hr_accommodation = process_hr_accommodation(hr_accommodation_submissions)
        if not df_hr_accommodation.empty:
            write_to_google_sheet(df_hr_accommodation, gc, HR_ACCOMMODATION_SHEET_NAME)
    
    print("\n" + "="*60)
    print("✅ Google Sheets Update Complete")
    print("="*60)

if __name__ == "__main__":
    main()
