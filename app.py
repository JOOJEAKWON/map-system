import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import re

# =============================================================================
# 1. 시스템 설정 & UI (Clean White / 실사용 최적화)
# =============================================================================
st.set_page_config(
    page_title="MAP INTEGRATED SYSTEM",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
<style>
.main {background-color:#FFFFFF; color:#333;}
.stForm {
    background:#F8F9FA;
    padding:20px;
    border-radius:12px;
    border:1px solid #E0E0E0;
}
.result-box {
    padding:25px;
    border-radius:12px;
    margin:20px 0;
    border-left:8px solid #ccc;
    line-height:1.6;
    box-shadow:0 2px 10px rgba(0,0,0,0.08);
}
.res-stop {background:#FFF0F0; border-left-color:#FF4B4B;}
.res-mod {background:#FFF8E1; border-left-color:#FFA500;}
.res-go {background:#E8F5E9; border-left-color:#00C853;}
.status-ok {color:#1f7a1f; font-weight:bold;}
.status-err {color:#cf1322; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. 유틸리티
# =============================================================================
def get_korea_timestamp():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

def extract_decision(text: str):
    t = text.upper()
    if "STOP" in t:
        return "STOP"
    if "MODIFICATION" in t:
        return "MODIFICATION"
    return "GO"

def extract_kakao_message(text: str):
    if "카카오" in text:
        return text.split("카카오")[-1][:500]
    return text[:300]

def safe_append_row(sheet, row):
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e:
        return False, str(e)

# =============================================================================
# 3. DB / AI 연결
# =============================================================================
def connect_db():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secrets 설정 누락"
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]), scope
        )
        client = gspread.authorize(creds)
        sheet = client.open("MAP_DATABASE").sheet1
        return sheet, "DB 연결 성공"
    except Exception as e:
        return None, str(e)

sheet, db_msg = connect_db()

if "OPENAI_API_KEY" in st.secrets:
    ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    ai_client = None

# =============================================================================
# 4. 사이드바 (상태)
# =============================================================================
st.sidebar.markdown("### SYSTEM STATUS")
if sheet:
    st.sidebar.markdown(f"<span class='status-ok'>● DB ONLINE</span>", unsafe_allow_html=True)
else:
    st.sidebar.markdown(f"<span class='status-err'>● DB OFFLINE</span>", unsafe_allow_html=True)
    st.sidebar.caption(db_msg)

if ai_client:
    st.sidebar.markdown("<span class='status-ok'>● AI READY</span>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("<span class='status-err'>● AI OFFLINE</span>", unsafe_allow_html=True)

# =============================================================================
# 5. MAP CORE PROMPT (확정본)
# =============================================================================
MAP_CORE_PROMPT = """
ROLE: Non-medical administrative safety system for gym operations.
PRIORITY: Legal safety > Operational consistency > Member experience.

RULES:
1. STOP: Direct pain-load conflict or high aggravation risk.
2. MODIFICATION: Potential risk, requires adjustment.
3. GO: No apparent biomechanical conflict.

OUTPUT FORMAT (Markdown):

Decision: STOP / MODIFICATION / GO
Reason: One dry, administrative sentence.
Guideline: One safe operational guideline sentence.
"""

# =============================================================================
# 6. 메인 UI
# =============================================================================
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.write(f"System Time (KST): {get_korea_timestamp()}")

tab1, tab2 = st.tabs(["PT 안전 분류", "시설 관리 로그"])

# =============================================================================
# TAB 1 – PT 안전 분류
# =============================================================================
with tab1:
    st.subheader("PT 수업 전 안전 분류")

    with st.form("pt_form"):
        col1, col2 = st.columns(2)
        with col1:
            member = st.text_input("회원 정보", placeholder="예: 50대 남성, 허리디스크")
            symptom = st.text_input("현재 컨디션/증상", placeholder="예: 허리 통증")
        with col2:
            exercise = st.text_input("예정 운동", placeholder="예: 데드리프트")
            send_kakao = st.checkbox("결과를 카카오톡으로 전송", value=True)

        submit = st.form_submit_button("분석 실행")

    if submit:
        if not (ai_client and sheet):
            st.error("AI 또는 DB 연결을 확인하십시오.")
        else:
            input_block = f"""
Member: {member}
Symptom: {symptom}
Exercise: {exercise}
"""

            with st.spinner("MAP CORE 분석 중..."):
                response = ai_client.chat.completions.create(
                    model="gpt-4o",
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": MAP_CORE_PROMPT},
                        {"role": "user", "content": input_block}
                    ]
                )

                full_res = response.choices[0].message.content
                decision = extract_decision(full_res)

                css = {
                    "STOP": "res-stop",
                    "MODIFICATION": "res-mod",
                    "GO": "res-go"
                }[decision]

                st.markdown(
                    f"<div class='result-box {css}'><strong>판정: {decision}</strong><br/><br/>{full_res}</div>",
                    unsafe_allow_html=True
                )

                ok, err = safe_append_row(
                    sheet,
                    [
                        get_korea_timestamp(),
                        "PT_ANALYSIS",
                        member,
                        symptom,
                        exercise,
                        decision,
                        full_res[:3000]
                    ]
                )

                if ok:
                    st.success("로그가 저장되었습니다.")
                else:
                    st.error(f"DB 저장 실패: {err}")

# =============================================================================
# TAB 2 – 시설 관리 로그
# =============================================================================
with tab2:
    st.subheader("시설 안전 관리 로그")

    with st.form("facility_form"):
        col1, col2 = st.columns(2)
        with col1:
            task = st.radio("작업 유형", ["시설 순찰", "기구 정비", "청소/환경", "기타"])
            location = st.radio("구역", ["유산소존", "웨이트존", "머신존", "탈의실/샤워실"])
        with col2:
            memo = st.text_input("특이사항", value="이상 없음")
            staff = st.text_input("점검자 이름")
            send_kakao_fac = st.checkbox("카카오톡 보고", value=True)

        save = st.form_submit_button("기록 저장")

    if save:
        if not sheet:
            st.error("DB 연결 실패")
        elif not staff:
            st.warning("점검자 이름을 입력하십시오.")
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
                st.success("시설 로그가 저장되었습니다.")
            else:
                st.error(f"저장 실패: {err}")
