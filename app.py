import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests # 카톡 전송을 위한 부품

# -----------------------------------------------------------------------------
# 1. 시스템 설정 & 스타일
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .main {background-color: #0E1117;}
    .status-badge {padding: 5px 10px; border-radius: 5px; font-weight: bold; color: white;}
    .result-box {padding: 15px; border-radius: 10px; margin: 10px 0; font-weight: bold; color: white;}
    .res-stop {background: #cf1322;} 
    .res-mod {background: #d48806;}
    .res-go {background: #1f7a1f;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 핵심 함수 (시간, DB, 카톡)
# -----------------------------------------------------------------------------
def get_korea_timestamp():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

def connect_db():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "❌ Secrets 설정 누락"
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        doc = client.open("MAP_DATABASE")
        sheet = doc.sheet1 
        return sheet, f"✅ 연결 성공"
    except Exception as e:
        return None, f"❌ 연결 실패: {str(e)}"

# [추가됨] 카카오톡 전송 함수
def send_kakao_message(text):
    try:
        if "KAKAO_TOKEN" not in st.secrets:
            return False, "토큰 없음"
        
        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        headers = {"Authorization": "Bearer " + st.secrets["KAKAO_TOKEN"]}
        data = {"template_object": str({
            "object_type": "text",
            "text": text,
            "link": {"web_url": "https://streamlit.io"}
        })}
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return True, "전송 성공"
        else:
            return False, f"전송 실패({response.status_code})"
    except Exception as e:
        return False, str(e)

def safe_append_row(sheet, row):
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e:
        return False, str(e)

# -----------------------------------------------------------------------------
# 3. 사이드바 (상태창)
# -----------------------------------------------------------------------------
st.sidebar.title("🔧 관리자 패널")
sheet, db_msg = connect_db()

if sheet:
    st.sidebar.success(db_msg)
else:
    st.sidebar.error(db_msg)

# 카톡 상태 확인
if "KAKAO_TOKEN" in st.secrets:
    st.sidebar.success("✅ 카카오톡 모듈 장착됨")
else:
    st.sidebar.warning("⚠️ 카톡 토큰 없음 (전송 안됨)")

if st.sidebar.button("DB 쓰기 테스트"):
    if sheet:
        sheet.append_row([get_korea_timestamp(), "DEBUG", "TEST", "OK"])
        st.sidebar.success("쓰기 성공")

if "OPENAI_API_KEY" in st.secrets:
    ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    ai_client = None

# -----------------------------------------------------------------------------
# 4. 메인 기능
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.write(f"🕒 Time (KST): {get_korea_timestamp()}")

tab1, tab2 = st.tabs(["🧬 PT 안전 분류", "🏢 시설 관리 로그"])

# === [TAB 1] PT 안전 분류 ===
with tab1:
    st.subheader("📋 PT 수업 전 행정적 안전 분류")
    with st.form("pt_form"):
        c1, c2 = st.columns(2)
        with c1:
            member = st.text_input("회원 정보", placeholder="50대 남성, 허리디스크")
            symptom = st.text_input("현재 상태", placeholder="오늘 허리 통증")
        with c2:
            exercise = st.text_input("예정 운동", placeholder="데드리프트")
            
        # 카톡 전송 여부 체크박스
        send_k = st.checkbox("결과를 카톡으로도 전송하기", value=True)
        btn = st.form_submit_button("⚡ 리스크 분석")

    if btn:
        if ai_client and sheet:
            with st.spinner("분석 중..."):
                try:
                    prompt = f"""
                    Role: Safety Administration Officer (Conservative).
                    Task: Risk categorize strictly (STOP/MODIFICATION/GO).
                    Input: Member '{member}', Symptom '{symptom}', Exercise '{exercise}'.
                    Output: 1st line decision, 2nd line short reason (Korean).
                    """
                    res = ai_client.chat.completions.create(
                        model="gpt-4o", messages=[{"role": "user", "content": prompt}]
                    ).choices[0].message.content
                    
                    # 결과 표시
                    if "STOP" in res: st.markdown(f"<div class='result-box res-stop'>⛔ {res}</div>", unsafe_allow_html=True)
                    elif "MODIFICATION" in res: st.markdown(f"<div class='result-box res-mod'>⚠️ {res}</div>", unsafe_allow_html=True)
                    else: st.markdown(f"<div class='result-box res-go'>✅ {res}</div>", unsafe_allow_html=True)
                    
                    # 저장
                    ok, _ = safe_append_row(sheet, [get_korea_timestamp(), "PT_SAFETY", member, symptom, exercise, res])
                    if ok:
                        st.success("💾 구글 시트 저장 완료")
                        # 카톡 전송 로직
                        if send_k:
                            msg = f"[MAP 알림]\n{get_korea_timestamp()}\n회원: {member}\n결과: {res}"
                            k_ok, k_msg = send_kakao_message(msg)
                            if k_ok: st.toast("💬 카톡 전송 완료!")
                            else: st.warning(f"카톡 실패: {k_msg}")
                    
                except Exception as e: st.error(f"에러: {e}")

# === [TAB 2] 시설 관리 ===
with tab2:
    st.subheader("🛠️ 시설 안전 점검 로그")
    with st.form("fac_form"):
        task = st.selectbox("점검 유형", ["오픈조 순찰", "마감조 순찰", "기구 정비"])
        place = st.selectbox("구역", ["웨이트존", "유산소존", "샤워실"])
        memo = st.text_input("특이사항", "이상 없음")
        staff = st.text_input("점검자")
        
        # 카톡 전송 여부 체크박스
        send_k_fac = st.checkbox("점검 완료 사실을 카톡으로 보고", value=True)
        save = st.form_submit_button("로그 저장")

    if save:
        if sheet:
            ok, err = safe_append_row(sheet, [get_korea_timestamp(), "FACILITY", task, place, memo, staff])
            if ok:
                st.success(f"✅ [{task}] 저장 완료")
                if send_k_fac:
                    msg = f"[시설 점검 보고]\n시간: {get_korea_timestamp()}\n점검자: {staff}\n유형: {task}\n특이사항: {memo}"
                    k_ok, k_msg = send_kakao_message(msg)
                    if k_ok: st.toast("💬 지점장님께 카톡 보고 완료!")
                    else: st.warning(f"카톡 전송 실패: {k_msg}")
            else: st.error(f"저장 실패: {err}")
