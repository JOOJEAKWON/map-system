import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import json

# -----------------------------------------------------------------------------
# 1. 시스템 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.main {background-color: #0E1117;}
.result-go {background:#1f7a1f; padding:15px; border-radius:10px; color:white; font-weight:bold;}
.result-mod {background:#d48806; padding:15px; border-radius:10px; color:white; font-weight:bold;}
.result-stop {background:#cf1322; padding:15px; border-radius:10px; color:white; font-weight:bold;}
.status-box {padding: 10px; border-radius: 5px; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 한국 시간 (KST)
# -----------------------------------------------------------------------------
def get_korea_timestamp():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------------------------------------------------------
# 3. 연결 상태 진단 (여기가 핵심!)
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.write(f"🕒 시스템 시간 (KST): **{get_korea_timestamp()}**")

# [1] 구글 시트 연결 시도
try:
    if "gcp_service_account" in st.secrets:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        sheet = client.open("MAP_DATABASE").sheet1
        # [수정된 코드] 시트 연결 및 주소 확인
        doc = client.open("MAP_DATABASE") # 파일 전체를 엽니다
        sheet = doc.sheet1 # 첫 번째 탭을 가져옵니다
        
        # 화면에 "진짜 파일 주소"를 링크로 띄워줍니다 (여기를 클릭해보세요!)
        st.success("✅ 구글 데이터베이스 연결 성공 (Online)")
        st.markdown(f"### 👉 [여기를 클릭해서 데이터가 쌓이는 엑셀 파일 열기](https://docs.google.com/spreadsheets/d/{doc.id})")
    else:
        sheet = None
        st.error("❌ 구글 시트 키가 Secrets에 없습니다. [gcp_service_account] 확인 필요")
except Exception as e:
    sheet = None
    st.error(f"❌ 구글 시트 연결 에러: {e}")

# [2] OpenAI 연결 시도
try:
    if "OPENAI_API_KEY" in st.secrets:
        ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        st.success("✅ AI 엔진(OpenAI) 가동 성공 (Ready)")
    else:
        ai_client = None
        st.error("❌ OpenAI API 키가 없습니다. Secrets에 [OPENAI_API_KEY]를 넣어주세요.")
except Exception as e:
    ai_client = None
    st.error(f"❌ AI 연결 에러: {e}")

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. 메인 기능 탭
# -----------------------------------------------------------------------------
tab1, tab2 = st.tabs(["🧬 PT 안전 분류 (AI)", "🏢 시설 관리 로그"])

# === [TAB 1] PT 안전 분류 ===
with tab1:
    st.subheader("📋 PT 수업 전 리스크 분석")
    
    with st.form("pt_form"):
        col1, col2 = st.columns(2)
        with col1:
            member_info = st.text_input("회원 정보", placeholder="예: 50대 남성, 척추관협착증")
            symptom = st.text_input("현재 통증/컨디션", placeholder="예: 오늘 허리 뻐근함 호소")
        with col2:
            exercise = st.text_input("수행 예정 운동", placeholder="예: 컨벤셔널 데드리프트")
            
        submit = st.form_submit_button("⚡ AI 분석 실행")

    # 버튼을 눌렀을 때 로직
    if submit:
        # 1. AI가 연결 안 되어 있으면 경고
        if not ai_client:
            st.error("🚨 AI가 연결되지 않아 분석할 수 없습니다. 위쪽 에러 메시지를 확인하세요.")
        
        # 2. 내용이 비어있으면 경고
        elif not member_info or not exercise:
            st.warning("⚠️ 회원 정보와 운동 종목을 입력해주세요.")
            
        # 3. 정상 실행
        else:
            with st.spinner("🧠 Singularity AI가 생체역학 데이터를 분석 중입니다..."):
                try:
                    system_prompt = """
                    You are a strict biomechanics safety officer.
                    Based on the member's condition and the exercise, classify the risk.
                    
                    RULES:
                    1. Direct conflict (e.g., Back pain + Deadlift) -> STOP
                    2. Indirect/Potential risk -> MODIFICATION
                    3. No risk -> GO
                    
                    OUTPUT FORMAT:
                    Start immediately with one word: STOP, MODIFICATION, or GO.
                    Then add a line break and explain why in Korean.
                    """
                    
                    user_input = f"Member: {member_info}, Condition: {symptom}, Exercise: {exercise}"
                    
                    response = ai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_input}
                        ]
                    )
                    
                    full_result = response.choices[0].message.content.strip()
                    
                    # 결과 디자인 출력
                    if full_result.startswith("STOP"):
                        st.markdown(f"<div class='result-stop'>⛔ {full_result}</div>", unsafe_allow_html=True)
                        decision = "STOP"
                    elif full_result.startswith("MODIFICATION"):
                        st.markdown(f"<div class='result-mod'>⚠️ {full_result}</div>", unsafe_allow_html=True)
                        decision = "MODIFICATION"
                    else:
                        st.markdown(f"<div class='result-go'>✅ {full_result}</div>", unsafe_allow_html=True)
                        decision = "GO"
                    
                    # 시트 저장
                    if sheet:
                        sheet.append_row([get_korea_timestamp(), "PT_AI_CHECK", member_info, symptom, exercise, decision])
                        st.toast("💾 구글 시트에 기록되었습니다.")
                    else:
                        st.warning("분석은 됐지만, 구글 시트 연결이 안 되어 저장은 실패했습니다.")
                        
                except Exception as e:
                    st.error(f"분석 중 오류 발생: {e}")

# === [TAB 2] 시설 관리 ===
with tab2:
    st.subheader("🛠️ 시설 안전 점검")
    with st.form("facility_form"):
        task = st.selectbox("점검 유형", ["오픈조 점검", "마감조 점검", "기구 정비", "청소"])
        location = st.selectbox("구역", ["웨이트존", "유산소존", "탈의실", "프리웨이트"])
        memo = st.text_input("특이사항 (없으면 '이상무')", "이상 없음")
        staff_name = st.text_input("점검자 서명")
        
        save_btn = st.form_submit_button("📝 기록 저장")
        
    if save_btn:
        if sheet and staff_name:
            sheet.append_row([get_korea_timestamp(), "FACILITY", task, location, memo, staff_name])
            st.success(f"✅ [{task}] 기록이 서버에 저장되었습니다.")
        elif not sheet:
            st.error("🚨 구글 시트 연결이 끊겨 있습니다.")
        elif not staff_name:
            st.warning("점검자 이름을 입력하세요.")

