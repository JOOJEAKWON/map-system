import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai

# -----------------------------------------------------------------------------
# 1. 시스템 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MAP INTEGRATED SYSTEM",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
<style>
.main {background-color: #0E1117;}
.result-go {background:#1f7a1f; padding:12px; border-radius:6px; color:white;}
.result-mod {background:#7a5c00; padding:12px; border-radius:6px; color:white;}
.result-stop {background:#7a1f1f; padding:12px; border-radius:6px; color:white;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 한국 시간 계산 (KST)
# -----------------------------------------------------------------------------
def get_korea_timestamp():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------------------------------------------------------
# 3. Google Sheet 연결
# -----------------------------------------------------------------------------
def connect_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Secrets에 gcp_service_account가 없습니다.")
            return None

        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]),
            scope
        )
        client = gspread.authorize(creds)

        sheet = client.open("MAP_DATABASE").sheet1
        st.success("구글 시트 연결 성공")
        return sheet

    except Exception as e:
        st.error(f"구글 시트 연결 실패: {e}")
        return None

# ⭐⭐⭐ 실제 연결 실행 (가장 중요)
sheet = connect_sheet()

# -----------------------------------------------------------------------------
# 4. OpenAI 연결 (이름 충돌 방지)
# -----------------------------------------------------------------------------
try:
    ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    ai_client = None

# -----------------------------------------------------------------------------
# 5. UI
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.markdown(f"시스템 시간 (KST): {get_korea_timestamp()}")

if sheet:
    st.success("데이터베이스 상태: ONLINE")
else:
    st.warning("데이터베이스 상태: OFFLINE (시트 공유 확인 필요)")

tab1, tab2 = st.tabs(["PT 사전 안전 분류", "시설 관리 로그"])

# =============================================================================
# [TAB 1] PT 사전 안전 분류
# =============================================================================
with tab1:
    st.subheader("PT 수업 전 안전 분류")

    with st.form("pt_form"):
        member_info = st.text_input("회원 정보", placeholder="예: 50대 남성, 허리디스크")
        symptom = st.text_input("현재 상태", placeholder="예: 무릎 통증")
        exercise = st.text_input("예정 운동", placeholder="예: 스쿼트")
        submit = st.form_submit_button("분류 실행")

    if submit and ai_client:
        system_prompt = """
ROLE: Non-medical Safety Classification System
RULE:
- Direct pain + same joint exercise → STOP
- Indirect conflict → MODIFICATION
- No conflict → GO
OUTPUT:
First word must be STOP / MODIFICATION / GO
"""

        user_input = f"""
Member: {member_info}
Symptom: {symptom}
Exercise: {exercise}
"""

        with st.spinner("AI 분석 중..."):
            response = ai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )

            result = response.choices[0].message.content.strip()
            decision = result.split()[0].upper()

            if decision == "STOP":
                st.markdown(f"<div class='result-stop'>{result}</div>", unsafe_allow_html=True)
            elif decision == "MODIFICATION":
                st.markdown(f"<div class='result-mod'>{result}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='result-go'>{result}</div>", unsafe_allow_html=True)

            # 로그 저장
            if sheet:
                sheet.append_row([
                    get_korea_timestamp(),
                    "PT_CHECK",
                    member_info,
                    symptom,
                    exercise,
                    decision
                ])
                st.toast("PT 로그가 구글 시트에 저장되었습니다.")

# =============================================================================
# [TAB 2] 시설 관리 로그
# =============================================================================
with tab2:
    st.subheader("시설 관리 기록")

    with st.form("facility_form"):
        task = st.selectbox("작업 유형", ["정기 순찰", "안전 교육", "기구 정비"])
        location = st.selectbox("구역", ["유산소존", "머신존", "프리웨이트존", "탈의실/샤워실"])
        action = st.text_input("조치 내용", placeholder="이상 없음")
        staff = st.text_input("점검자 이름")
        save = st.form_submit_button("기록 저장")

    if save:
        if sheet:
            sheet.append_row([
                get_korea_timestamp(),
                "FACILITY_LOG",
                task,
                location,
                action,
                staff
            ])
            st.success("시설 로그가 구글 시트에 저장되었습니다.")
        else:
            st.error("시트 연결 실패로 저장되지 않았습니다.")
