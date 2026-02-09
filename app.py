import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai

# -----------------------------------------------------------------------------
# 1. 시스템 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.main {background-color: #0E1117;}
.result-box {padding:15px; border-radius:10px; color:white; font-weight:bold; margin-bottom:10px;}
.go {background:#1f7a1f;}
.mod {background:#d48806;}
.stop {background:#cf1322;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 한국 시간 (KST)
# -----------------------------------------------------------------------------
def get_korea_timestamp():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------------------------------------------------------
# 3. 연결 및 진단
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.write(f"🕒 시스템 시간 (KST): **{get_korea_timestamp()}**")

# [구글 시트 연결]
try:
    if "gcp_service_account" in st.secrets:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        sheet = client.open("MAP_DATABASE").sheet1
        
        # 진짜 파일 바로가기 링크 생성 (편의 기능)
        file_url = f"https://docs.google.com/spreadsheets/d/{sheet.spreadsheet.id}"
        st.success("✅ 구글 데이터베이스 연결 성공 (Online)")
        st.markdown(f"👉 **[데이터가 쌓이는 엑셀 파일 바로가기 (클릭)]({file_url})**")
    else:
        sheet = None
        st.error("❌ Secrets 설정 오류: [gcp_service_account]가 없습니다.")
except Exception as e:
    sheet = None
    st.error(f"❌ 구글 시트 연결 실패: {e}")

# [OpenAI 연결]
try:
    if "OPENAI_API_KEY" in st.secrets:
        ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        st.success("✅ AI 엔진(OpenAI) 가동 성공 (Ready)")
    else:
        ai_client = None
        st.warning("⚠️ OpenAI 키가 없습니다. AI 분석 기능은 작동하지 않습니다.")
except Exception as e:
    ai_client = None
    st.error(f"❌ AI 연결 에러: {e}")

st.divider()

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
            member_info = st.text_input("회원 정보", "50대 남성, 허리디스크")
            symptom = st.text_input("현재 상태", "오늘 약간 뻐근함")
        with col2:
            exercise = st.text_input("운동 종목", "데드리프트")
        
        submit = st.form_submit_button("⚡ AI 분석 실행")
        
    if submit:
        if not ai_client:
            st.error("🚨 AI가 연결되지 않았습니다.")
        elif not sheet:
            st.error("🚨 구글 시트가 연결되지 않았습니다.")
        else:
            with st.spinner("AI 분석 중..."):
                try:
                    # AI에게 질문
                    prompt = f"회원: {member_info}, 증상: {symptom}, 운동: {exercise}. 위험도를 STOP, MODIFICATION, GO 중 하나로 판단하고 한 줄로 이유를 설명해."
                    response = ai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    result = response.choices[0].message.content
                    
                    # 결과 보여주기
                    if "STOP" in result:
                        st.markdown(f"<div class='result-box stop'>⛔ {result}</div>", unsafe_allow_html=True)
                        decision = "STOP"
                    elif "MODIFICATION" in result:
                        st.markdown(f"<div class='result-box mod'>⚠️ {result}</div>", unsafe_allow_html=True)
                        decision = "MODIFICATION"
                    else:
                        st.markdown(f"<div class='result-box go'>✅ {result}</div>", unsafe_allow_html=True)
                        decision = "GO"

                    # 시트 저장
                    sheet.append_row([get_korea_timestamp(), "PT_AI_CHECK", member_info, symptom, exercise, decision])
                    st.toast("💾 저장 완료! 위쪽 링크를 눌러 확인하세요.")
                    
                except Exception as e:
                    st.error(f"에러 발생: {e}")

# === [TAB 2] 시설 관리 ===
with tab2:
    st.subheader("🛠️ 시설 안전 점검")
    with st.form("facility_form"):
        task = st.selectbox("점검 유형", ["오픈조 점검", "마감조 점검", "기구 정비", "청소"])
        place = st.selectbox("구역", ["웨이트존", "유산소존", "탈의실", "프리웨이트"])
        memo = st.text_input("특이사항", "이상 없음")
        name = st.text_input("점검자")
        save_btn = st.form_submit_button("📝 기록 저장")
        
    if save_btn:
        if sheet:
            sheet.append_row([get_korea_timestamp(), "FACILITY", task, place, memo, name])
            st.success("✅ 저장 완료! 위쪽 링크를 눌러 엑셀을 확인하세요.")
        else:
            st.error("🚨 시트 연결 안됨")
