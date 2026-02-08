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
# 2. 한국 시간 계산 함수 (KST Patch)
# -----------------------------------------------------------------------------
def get_korea_timestamp():
    # 서버 시간(UTC)에 9시간을 더해서 한국 시간을 만듭니다
    utc_now = datetime.utcnow()
    korea_now = utc_now + timedelta(hours=9)
    return korea_now.strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------------------------------------------------------
# 3. Google Sheet 연결
# -----------------------------------------------------------------------------
def connect_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        # 금고 확인
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets 설정이 비어있습니다.")
            return None

        # 연결 시도
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]),
            scope
        )
        client = gspread.authorize(creds)
        sheet = client.open("MAP_DATABASE").sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ 구글 시트 연결 실패: {e}")
        return None

sheet = connect_sheet()

# -----------------------------------------------------------------------------
# 4. OpenAI 연결
# -----------------------------------------------------------------------------
try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    client = None

# -----------------------------------------------------------------------------
# 5. UI 및 로직
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.markdown(f"🕒 **System Time (KST):** {get_korea_timestamp()}") # 현재 시간 표시

if sheet:
    st.success("🟢 데이터베이스 연결됨 (Online)")
else:
    st.warning("🔴 데이터베이스 연결 끊김 (Offline) - 구글 시트 공유를 확인하세요.")

tab1, tab2 = st.tabs(["PT 사전 안전 분류", "시설 관리 로그"])

# [TAB 1] PT 안전 분류
with tab1:
    st.subheader("PT 수업 전 안전 분류")
    with st.form("pt_form"):
        member_info = st.text_input("회원 정보", placeholder="예: 50대 남성, 허리디스크")
        symptom = st.text_input("현재 상태", placeholder="예: 오늘 허리가 좀 뻐근함")
        exercise = st.text_input("예정 운동", placeholder="예: 데드리프트")
        submit = st.form_submit_button("분류 실행")

    if submit and client:
        # 프롬프트 설정
        system_prompt = """
        ROLE: Non-medical Safety Classification System
        OUTPUT: JSON style text
        DECISION: STOP / MODIFICATION / GO
        Risk analysis based on biomechanics.
        """
        user_input = f"Member: {member_info}, Symptom: {symptom}, Exercise: {exercise}"
        
        with st.spinner("AI가 분석 중입니다..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )
            result = response.choices[0].message.content

            # 결과 화면 출력
            if "STOP" in result:
                st.markdown(f"<div class='result-stop'>⛔ {result}</div>", unsafe_allow_html=True)
            elif "MODIFICATION" in result:
                st.markdown(f"<div class='result-mod'>⚠️ {result}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='result-go'>✅ {result}</div>", unsafe_allow_html=True)

            # 시트 저장
            if sheet:
                sheet.append_row([
                    get_korea_timestamp(), # 한국 시간 저장
                    "PT_CHECK",
                    member_info,
                    symptom,
                    exercise,
                    result[:100]
                ])
                st.toast("💾 구글 시트에 저장 완료!")

# [TAB 2] 시설 관리 로그
with tab2:
    st.subheader("시설 관리 기록")
    with st.form("facility_form"):
        task = st.selectbox("작업 유형", ["정기 순찰", "안전 교육", "기구 정비", "청소 상태"])
        location = st.selectbox("구역", ["유산소존", "머신존", "프리웨이트존", "탈의실/샤워장"])
        action = st.text_input("특이 사항", placeholder="이상 없음")
        staff = st.text_input("점검자 이름")
        save = st.form_submit_button("기록 저장")

    if save:
        if sheet:
            sheet.append_row([
                get_korea_timestamp(), # 한국 시간 저장
                "FACILITY_LOG",
                task,
                location,
                action,
                staff
            ])
            st.success(f"✅ [{task}] 기록이 저장되었습니다. (시간: {get_korea_timestamp()})")
        else:
            st.error("데이터베이스 연결 실패. 기록이 저장되지 않았습니다.")


