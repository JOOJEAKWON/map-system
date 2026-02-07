import streamlit as st
import openai
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------------------------------------------------
# [구글 시트 연결 설정]
# ---------------------------------------------------------
def save_to_google_sheets(data):
    try:
        # 인증 범위 설정
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # json 파일 이름이 정확해야 합니다.
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
        client = gspread.authorize(creds)
        
        # 시트 열기
        sheet = client.open("MAP_DATABASE").sheet1
        sheet.append_row(data)
        return True
    except Exception as e:
        st.error(f"구글 시트 저장 실패: {e}")
        return False

# ---------------------------------------------------------
# 1. 기본 설정 & UI
# ---------------------------------------------------------
st.set_page_config(page_title="MAP SAFETY SYSTEM", page_icon="🛡️", layout="centered")

# (기존 CSS 스타일 유지...)
st.markdown("""<style>html, body, [class*="css"] { font-size: 14px !important; } .kakao-box {background: #f1f3f5; padding: 12px; border-radius: 8px;}</style>""", unsafe_allow_html=True)

api_key = st.secrets.get("OPENAI_API_KEY")
client = openai.OpenAI(api_key=api_key)

# (SYSTEM_PROMPT 및 헬퍼 함수 기존 동일 유지...)
# ... (재권 님이 가지고 계신 v3.0 코드의 앞부분과 동일) ...

st.title("🛡️ MAP INTEGRATED SYSTEM")
st.markdown("**Status:** `OPERATIONAL` 🟢 | **Mode:** `ENTERPRISE_LOG` 🏢")

tab1, tab2 = st.tabs(["🏋️ PT 컨디션 체크 (회원용)", "🚨 시설 안전 점검 (직원용)"])

# [TAB 1] PT (기존 코드 유지)
with tab1:
    # ... (기존 PT 코드) ...
    st.info("PT 기능은 로컬에서만 작동합니다. (시설 점검이 중요)")

# =========================================================
# [TAB 2] 시설 안전 점검 (구글 시트 연동)
# =========================================================
with tab2:
    st.markdown("### ⚠️ 시설 안전 점검 로그 (Enterprise)")
    st.caption("※ 본 기록은 **킹스짐 전 지점**의 구글 시트 데이터베이스로 전송됩니다.")

    with st.form("facility_form"):
        branch_name = st.selectbox("지점 선택", ["킹스짐 1호점 (본점)", "킹스짐 2호점", "킹스짐 3호점"])
        task_type = st.radio("점검 유형", ["🔄 정기 순찰", "🎓 신규/안전 교육", "🛠️ 기구 정비"])
        target_zone = st.selectbox("점검 구역", ["ZONE A (유산소)", "ZONE B (프리웨이트)", "ZONE C (머신존)", "ZONE D (탈의실)"])
        
        st.markdown("**✅ 현장 확인**")
        chk_1 = st.checkbox("항목 1 확인 (기구/위험고지/수리)")
        chk_2 = st.checkbox("항목 2 확인 (환경/시연/테스트)")
        
        staff_name = st.text_input("점검자 실명")
        submitted_facility = st.form_submit_button("💾 안전 점검 로그 저장")

    if submitted_facility:
        if not staff_name or not (chk_1 or chk_2):
             st.warning("⚠️ 이름과 체크박스를 확인해주세요.")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 1. 화면에 로그 띄우기 (기존 기능)
            log_text = f"[{branch_name}] {task_type} / {target_zone} / {staff_name} / {now}"
            st.success(f"✅ 저장 완료: {log_text}")
            
            # 2. [NEW] 구글 시트로 데이터 전송!
            data_to_save = [now, branch_name, task_type, target_zone, "CHECKED_OK", staff_name]
            
            if save_to_google_sheets(data_to_save):
                st.toast("☁️ 구글 클라우드 업로드 완료!", icon="🚀")
            else:
                st.error("클라우드 전송 실패. 인터넷 연결을 확인하세요.")