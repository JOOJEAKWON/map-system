import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
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
.result-go {background:#1f7a1f; padding:12px; border-radius:6px;}
.result-mod {background:#7a5c00; padding:12px; border-radius:6px;}
.result-stop {background:#7a1f1f; padding:12px; border-radius:6px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Google Sheet 연결 (로그 저장)
# -----------------------------------------------------------------------------
def connect_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        # 1. 금고 확인
        if "gcp_service_account" not in st.secrets:
            st.error("❌ 에러: Secrets에 [gcp_service_account]가 없습니다.")
            return None

        # 2. 인증 시도
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]),
            scope
        )
        client = gspread.authorize(creds)
        
        # 3. 시트 열기
        sheet = get_google_sheet_connection()

if sheet is None:
    st.error("❌ DEBUG: 구글 시트 연결 실패 (sheet is None)")
else:
    st.success("✅ DEBUG: 구글 시트 연결 성공")
    st.write("Sheet object:", sheet)

# -----------------------------------------------------------------------------
# 3. OpenAI 연결
# -----------------------------------------------------------------------------
try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    client = None

# -----------------------------------------------------------------------------
# 4. SMART-LITE 행정 판단 프롬프트 (확정본)
# -----------------------------------------------------------------------------
SYSTEM_PROMPT = """
# MASTER SYSTEM: MAP_INTEGRATED_CORE_v2026 (SMART-LITE)
# ROLE: Non-medical Safety Classification System

[ABSOLUTE RULES]
- Do NOT provide medical advice or diagnosis.
- Do NOT explain anatomical mechanisms.
- Do NOT persuade or reassure emotionally.
- This system classifies risk for operational records only.

[CLASSIFICATION LOGIC]
1. If pain area directly overlaps with exercise load area -> STOP
2. If indirect overlap or uncertainty exists -> MODIFICATION
3. If no overlap -> GO
4. Upper pain + lower exercise OR lower pain + upper exercise -> GO

[OUTPUT FORMAT]
Return ONLY the following structure:

[DECISION]: GO / MODIFICATION / STOP
[RISK_NOTE]: One neutral sentence describing overlap or non-overlap.
[OPERATION_GUIDE]:
- Limit:
- Alternative:
- Cue:

[KAKAO_TEXT]:
One neutral sentence for member notice.
"""

# -----------------------------------------------------------------------------
# 5. UI
# -----------------------------------------------------------------------------
st.title("MAP INTEGRATED SYSTEM")
tab1, tab2 = st.tabs(["PT 사전 안전 분류", "시설 관리 로그"])

# -----------------------------------------------------------------------------
# TAB 1 : PT 사전 안전 분류 (행정 판단)
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("PT 수업 전 안전 분류")

    with st.form("pt_form"):
        member_info = st.text_input("회원 정보")
        symptom = st.text_input("현재 상태")
        exercise = st.text_input("예정 운동")
        submit = st.form_submit_button("분류 실행")

    if submit:
        if not client:
            st.error("AI 연결 오류")
        else:
            user_input = f"""
회원 정보: {member_info}
현재 상태: {symptom}
예정 운동: {exercise}
"""
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input}
                ],
                temperature=0
            )

            result = response.choices[0].message.content

            if "[DECISION]: STOP" in result:
                st.markdown("<div class='result-stop'>STOP</div>", unsafe_allow_html=True)
            elif "[DECISION]: MODIFICATION" in result:
                st.markdown("<div class='result-mod'>MODIFICATION</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='result-go'>GO</div>", unsafe_allow_html=True)

            st.markdown(result)

            # 로그 저장
            if sheet:
                sheet.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "PT_CHECK",
                    member_info,
                    symptom,
                    exercise,
                    result.replace("\n", " ")
                ])

# -----------------------------------------------------------------------------
# TAB 2 : 시설 관리 로그 (Dry Log)
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("시설 관리 기록")

    with st.form("facility_form"):
        task = st.selectbox(
            "작업 유형",
            ["정기 순찰", "안전 교육", "기구 정비"]
        )
        location = st.selectbox(
            "구역",
            ["유산소존", "머신존", "프리웨이트존", "탈의실"]
        )
        action = st.text_input("수행 내용 (사실만 기재)")
        staff = st.text_input("직원 이름")
        save = st.form_submit_button("기록 저장")

    if save:
        if sheet:
            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "FACILITY_LOG",
                task,
                location,
                action,
                staff
            ])
        st.success("기록이 저장되었습니다.")



