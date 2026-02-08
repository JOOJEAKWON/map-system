import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import openai

# -----------------------------------------------------------------------------
# 1. 페이지 설정 (가장 먼저 실행)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP SYSTEM (Enterprise)", page_icon="🛡️", layout="centered")

# -----------------------------------------------------------------------------
# 2. 통합 인증 (파일이 있으면 파일로, 없으면 금고(Secrets)로 접속)
# -----------------------------------------------------------------------------
def get_google_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # 1순위: 클라우드 금고(Secrets) 확인
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        # 2순위: 로컬 파일 확인 (재권님 컴퓨터용)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
            
        client = gspread.authorize(creds)
        # 시트 이름이 맞는지 꼭 확인하세요! (기본값: MAP_DATABASE)
        sheet = client.open("MAP_DATABASE").sheet1 
        return sheet
    except Exception as e:
        st.error(f"❌ 구글 시트 연결 실패: {e}")
        return None

# 시트 연결 시도
sheet = get_google_sheet_connection()

# -----------------------------------------------------------------------------
# 3. OpenAI 설정
# -----------------------------------------------------------------------------
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = openai.OpenAI(api_key=api_key)
except Exception:
    # 로컬 테스트용 (혹시 금고가 없을 때)
    client = None 

# -----------------------------------------------------------------------------
# 4. 앱 헤더
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.caption(f"Status: OPERATIONAL 🟢 | Mode: ENTERPRISE_LOG 🏢")
st.markdown("---")

# -----------------------------------------------------------------------------
# 5. 메인 탭 구성
# -----------------------------------------------------------------------------
tab1, tab2 = st.tabs(["🏋️ PT 컨디션 체크 (회원용)", "🚨 시설 안전 점검 (직원용)"])

# === [TAB 1] PT 회원 컨디션 체크 ===
with tab1:
    st.header("📋 회원 컨디션 리포트")
    st.info("회원님의 오늘 상태를 체크하여 AI가 운동 강도를 추천합니다.")

    # 입력 폼
    with st.form("pt_form"):
        col1, col2 = st.columns(2)
        with col1:
            member_name = st.text_input("회원 이름", placeholder="예: 홍길동")
            condition = st.slider("오늘 컨디션 (1=최악, 10=최고)", 1, 10, 7)
        with col2:
            pain_level = st.select_slider("통증 정도", options=["없음", "약간", "보통", "심함", "매우 심함"])
            sleep_hours = st.number_input("수면 시간(시간)", min_value=0, max_value=24, value=7)
        
        issue_text = st.text_area("특이 사항 (통증 부위 등)", placeholder="어깨가 약간 뻐근함...")
        
        submit_pt = st.form_submit_button("✅ 리포트 생성 및 저장")

    if submit_pt:
        if not member_name:
            st.warning("회원 이름을 입력해주세요.")
        else:
            # 1. AI 분석 (OpenAI)
            ai_advice = "AI 분석을 사용할 수 없습니다."
            if client:
                try:
                    prompt = f"""
                    회원명: {member_name}
                    컨디션: {condition}/10
                    통증: {pain_level}
                    수면: {sleep_hours}시간
                    특이사항: {issue_text}
                    
                    위 정보를 바탕으로 트레이너에게 3줄 요약 조언을 해줘. 말투는 '해요체'로 부드럽게.
                    """
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    ai_advice = response.choices[0].message.content
                except Exception as e:
                    ai_advice = f"(AI 연결 오류: {e})"
            
            # 2. 결과 출력
            st.success(f"[{member_name}] 님 리포트 생성 완료!")
            st.markdown(f"**🤖 AI 코칭 가이드:**\n{ai_advice}")

            # 3. 구글 시트 저장
            if sheet:
                try:
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # 저장 포맷: [시간, 지점, 분류, 내용, 조치, 담당자] (양식에 맞춰 유동적 사용)
                    row_data = [now, "통합", "PT_REPORT", f"{member_name} (컨디션:{condition})", ai_advice, "AI_SYSTEM"]
                    sheet.append_row(row_data)
                    st.toast("☁️ 클라우드 데이터베이스 저장 완료!")
                except Exception as e:
                    st.error(f"구글 시트 저장 실패: {e}")

# === [TAB 2] 시설 안전 점검 ===
with tab2:
    st.header("⚠️ 시설 안전 점검 로그 (Enterprise)")
    st.caption("※ 본 기록은 킹스짐 전 지점의 구글 시트 데이터베이스로 전송됩니다.")

    branch = st.selectbox("지점 선택", ["킹스짐 1호점 (본점)", "킹스짐 2호점", "킹스짐 3호점"])
    
    check_type = st.radio("점검 유형", ["🔄 정기 순찰", "🎓 신규/안전 교육", "🛠 기구 정비"], horizontal=True)

    location = st.selectbox("점검 구역", ["ZONE A (유산소)", "ZONE B (웨이트)", "ZONE C (프리웨이트)", "샤워실/탈의실", "기타"])

    st.markdown("#### ✅ 체크리스트")
    chk1 = st.checkbox("현장 확인")
    chk2 = st.checkbox("항목 1 확인 (기구/위험고지/수리)")
    chk3 = st.checkbox("항목 2 확인 (환경/시연/테스트)")
    
    staff_name = st.text_input("점검자 실명")

    if st.button("💾 안전 점검 로그 저장"):
        if not staff_name:
            st.error("점검자 이름을 입력하세요.")
        elif not chk1:
            st.error("'현장 확인'은 필수입니다.")
        else:
            if sheet:
                try:
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    status = "CHECKED_OK"
                    
                    # 데이터 전송
                    row = [now, branch, check_type, location, status, staff_name]
                    sheet.append_row(row)
                    
                    st.success(f"✅ 저장 완료: [{branch}] {check_type} / {location} / {staff_name} / {now}")
                    st.balloons()
                except Exception as e:
                    st.error(f"구글 시트 저장 실패: {e}")
                    st.error("클라우드 전송 실패. 인터넷 연결을 확인하세요.")
            else:
                st.error("데이터베이스 연결이 끊겨 있습니다.")
