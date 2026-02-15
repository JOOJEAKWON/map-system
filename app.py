import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import pandas as pd
import json
import re
import time

# -----------------------------------------------------------------------------
# 1. 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

# -----------------------------------------------------------------------------
# 2. 시간 (KST 고정)
# -----------------------------------------------------------------------------
def get_korea_timestamp():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------------------------------------------------------
# 3. DB 연결 (강화 + 명확한 오류 출력)
# -----------------------------------------------------------------------------
def connect_db():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secrets 누락"

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]),
            scope
        )

        client = gspread.authorize(creds)
        doc = client.open("MAP_DATABASE")
        sheet = doc.sheet1

        return sheet, "ONLINE"

    except Exception as e:
        return None, f"DB ERROR: {e}"

# -----------------------------------------------------------------------------
# 4. 안전한 DB 저장 (재시도 로직 포함)
# -----------------------------------------------------------------------------
def safe_append_row(sheet, row, retry=2):
    for i in range(retry):
        try:
            sheet.append_row(row, value_input_option="USER_ENTERED")
            return True, None
        except Exception as e:
            time.sleep(1)
            last_error = str(e)
    return False, last_error

# -----------------------------------------------------------------------------
# 5. 카카오 전송 (JSON 직렬화 안정화)
# -----------------------------------------------------------------------------
def send_kakao_message(text):
    if "KAKAO_TOKEN" not in st.secrets:
        return False, "토큰 없음"

    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": "Bearer " + st.secrets["KAKAO_TOKEN"]}

    payload = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": "https://map-system.local"}
    }

    data = {"template_object": json.dumps(payload)}

    res = requests.post(url, headers=headers, data=data)

    if res.status_code == 200:
        return True, None
    else:
        return False, res.text

# -----------------------------------------------------------------------------
# 6. 판정 단일화 로직 (법정 방어 핵심)
# -----------------------------------------------------------------------------
def normalize_decision(text):

    text_upper = text.upper()

    if "STOP" in text_upper:
        return "STOP"

    if "MODIFICATION" in text_upper:
        return "MODIFICATION"

    if "GO" in text_upper:
        return "GO"

    return "UNKNOWN"

# -----------------------------------------------------------------------------
# 7. OpenAI 연결
# -----------------------------------------------------------------------------
if "OPENAI_API_KEY" in st.secrets:
    ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    ai_client = None

# -----------------------------------------------------------------------------
# 8. DB 연결 실행
# -----------------------------------------------------------------------------
sheet, db_status = connect_db()

# -----------------------------------------------------------------------------
# 9. UI 상단
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM – DEFENSE EDITION")
st.write(f"System Time (KST): {get_korea_timestamp()}")
st.write(f"Database Status: {db_status}")

# -----------------------------------------------------------------------------
# 10. 탭 구성
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(
    ["PT Safety Analysis", "Facility Log", "Admin Dashboard"]
)

# =============================================================================
# [TAB 1] PT SAFETY ANALYSIS
# =============================================================================
with tab1:

    st.subheader("PT Administrative Safety Classification")

    with st.form("pt_form"):
        member = st.text_input("Member Info")
        symptom = st.text_input("Current Condition")
        exercise = st.text_input("Planned Exercise")
        send_kakao = st.checkbox("Send Kakao Message", value=True)
        submit = st.form_submit_button("Run Analysis")

    if submit:

        if not ai_client:
            st.error("AI not connected")
        elif not sheet:
            st.error("Database not connected")
        else:
            prompt = f"""
You are a gym safety administration system.
Categorize strictly as STOP / MODIFICATION / GO.

Member: {member}
Condition: {symptom}
Exercise: {exercise}
"""

            response = ai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )

            raw_text = response.choices[0].message.content
            decision = normalize_decision(raw_text)

            # 시각 출력
            if decision == "STOP":
                st.error(raw_text)
            elif decision == "MODIFICATION":
                st.warning(raw_text)
            elif decision == "GO":
                st.success(raw_text)
            else:
                st.info(raw_text)

            # 로그 저장 (판정값은 반드시 단일화된 값으로 저장)
            ok, err = safe_append_row(
                sheet,
                [
                    get_korea_timestamp(),
                    "PT_ANALYSIS",
                    member,
                    symptom,
                    exercise,
                    decision,
                    raw_text[:3000]
                ]
            )

            if not ok:
                st.error(f"DB 저장 실패: {err}")

            # 카카오 전송
            if send_kakao:
                k_ok, k_err = send_kakao_message(raw_text)
                if not k_ok:
                    st.warning(f"Kakao 실패: {k_err}")

# =============================================================================
# [TAB 2] FACILITY LOG
# =============================================================================
with tab2:

    st.subheader("Facility Safety Log")

    with st.form("facility_form"):
        task = st.selectbox("Task Type", ["Patrol", "Maintenance", "Cleaning"])
        location = st.selectbox("Location", ["Cardio", "Weight", "Locker"])
        memo = st.text_input("Notes", "Clear")
        staff = st.text_input("Staff Name")
        save = st.form_submit_button("Save Log")

    if save:
        if not staff:
            st.warning("Staff name required")
        elif not sheet:
            st.error("DB not connected")
        else:
            ok, err = safe_append_row(
                sheet,
                [
                    get_korea_timestamp(),
                    "FACILITY_LOG",
                    task,
                    location,
                    memo,
                    staff
                ]
            )

            if ok:
                st.success("Saved")
            else:
                st.error(f"Save failed: {err}")

# =============================================================================
# [TAB 3] ADMIN DASHBOARD
# =============================================================================
with tab3:

    if not sheet:
        st.warning("DB not connected")
    else:
        data = sheet.get_all_values()

        if len(data) > 1:

            df = pd.DataFrame(data[1:], columns=data[0])

            st.metric("Total Records", len(df))

            st.dataframe(df.sort_values(by=df.columns[0], ascending=False))

            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Download CSV", csv, "map_logs.csv", "text/csv")

        else:
            st.info("No data")
