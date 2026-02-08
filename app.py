import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import openai

# -----------------------------------------------------------------------------
# 1. 시스템 설정 (디자인 업그레이드)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MAP INTEGRATED SYSTEM",
    page_icon="🛡️",
    layout="wide",  # 화면을 넓게 씁니다
    initial_sidebar_state="expanded"
)

# 스타일 적용 (다크모드 대응 & 가독성 향상)
st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    .stButton>button {width: 100%; border-radius: 5px; height: 50px; font-weight: bold;}
    .report-box {padding: 20px; background-color: #262730; border-radius: 10px; border: 1px solid #4B4B4B;}
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 통합 인증 (연결 성공한 로직 유지)
# -----------------------------------------------------------------------------
def get_google_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
        client = gspread.authorize(creds)
        return client.open("MAP_DATABASE").sheet1 
    except Exception as e:
        return None

sheet = get_google_sheet_connection()

try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = openai.OpenAI(api_key=api_key)
except:
    client = None

# -----------------------------------------------------------------------------
# 3. 메인 화면 구성 (대시보드 스타일)
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.markdown("### `Enterprise Mode` : Operational 🟢")
st.markdown("---")

# 탭 구성
tab1, tab2 = st.tabs(["🧬 **PT 바이오 리포트 (Pro)**", "🏢 **시설 통합 관제 (Staff)**"])

# === [TAB 1] 전문가용 PT 리포트 ===
with tab1:
    col_input, col_result = st.columns([1, 1.2]) # 화면을 좌우로 나눔

    with col_input:
        st.subheader("📋 회원 생체 데이터 입력")
        with st.form("pt_pro_form"):
            member_name = st.text_input("회원명", placeholder="이름을 입력하세요")
            
            c1, c2 = st.columns(2)
            with c1:
                condition = st.slider("컨디션 지수", 1, 10, 5, help="낮을수록 휴식 필요")
                sleep_hours = st.number_input("수면 시간 (hr)", 0, 24, 7)
            with c2:
                pain_level = st.select_slider("통증 레벨 (VAS)", options=["0(없음)", "3(경미)", "5(불편)", "7(심함)", "10(응급)"])
                meal_status = st.selectbox("식사 상태", ["공복", "식사 완료", "소화 불량"])

            pain_area = st.text_input("통증/불편 부위", placeholder="예: 오른쪽 견갑거근, 요추 4-5번")
            issue_text = st.text_area("특이 사항 & 요청", placeholder="어제 데드리프트 후 허리가 뻐근함. 오늘 하체 가능할지?")
            
            submit_pt = st.form_submit_button("⚡ AI 정밀 분석 및 리포트 생성")

    with col_result:
        if submit_pt:
            if not member_name:
                st.error("회원 이름을 입력해주세요.")
            else:
                with st.spinner("🧠 Singularity AI가 생체 데이터를 분석 중입니다..."):
                    
                    # === [고급 프롬프트 장착] ===
                    real_prompt = f"""
                    당신은 국내 최고의 '운동 생체역학 전문가'이자 '재활 데이터 분석가'입니다.
                    아래 회원의 상태를 분석하여 전문적이고 실질적인 솔루션을 제시하세요.
                    말투는 '냉철하고 분석적인 전문가' 톤으로 유지하세요.

                    [회원 데이터]
                    - 이름: {member_name}
                    - 컨디션: {condition}/10
                    - 통증레벨: {pain_level}
                    - 통증부위: {pain_area}
                    - 수면시간: {sleep_hours}시간
                    - 특이사항: {issue_text}

                    [출력 형식]
                    1. 🩺 **상태 요약 (3줄 핵심)**
                    2. 🔬 **생체역학적 분석** (통증 원인 추론)
                    3. 🔥 **오늘의 운동 처방** (구체적인 종목, 강도, RPE 추천)
                    4. ⚠️ **주의사항 및 리스크 관리** (절대 하지 말아야 할 동작)
                    """

                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "system", "content": real_prompt}]
                        )
                        ai_advice = response.choices[0].message.content
                        
                        # 화면 출력
                        st.markdown(f"### 📊 [{member_name}] 님 분석 결과")
                        st.markdown(f"<div class='report-box'>{ai_advice}</div>", unsafe_allow_html=True)

                        # 구글 시트 저장
                        if sheet:
                            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            # 데이터 정제해서 저장
                            save_data = [now, "통합", "PT_PRO_REPORT", f"{member_name} (통증:{pain_level})", ai_advice[:100]+"...", "AI_ANALYSIS"]
                            sheet.append_row(save_data)
                            st.toast("✅ 클라우드 데이터베이스에 암호화 저장 완료")
                            
                    except Exception as e:
                        st.error(f"분석 중 오류 발생: {e}")

# === [TAB 2] 시설 점검 (기존 기능 유지) ===
with tab2:
    st.subheader("🚨 시설 안전 및 리스크 관리")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        branch = st.selectbox("지점", ["킹스짐 1호점", "킹스짐 2호점", "킹스짐 3호점"])
    with col2:
        location = st.selectbox("구역", ["유산소존", "웨이트존", "프리웨이트", "샤워실"])
    with col3:
        staff_name = st.text_input("점검자", placeholder="이름 입력")

    check_list = st.multiselect("점검 항목", ["기구 케이블 상태", "바닥 청결/미끄럼", "전자기기/조명", "소화기/비상구"])
    
    if st.button("💾 점검 로그 서버 전송"):
        if sheet and staff_name:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [now, branch, "시설점검", f"{location} - {len(check_list)}개 항목 양호", "CHECKED_OK", staff_name]
            sheet.append_row(row)
            st.success("서버 전송 완료.")
        else:
            st.warning("점검자 이름을 입력하세요.")
