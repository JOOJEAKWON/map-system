import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import re

# -----------------------------------------------------------------------------
# 1. 시스템 설정 & 스타일 (가독성 패치 적용)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .main {background-color: #0E1117;}
    
    /* 결과 박스 공통 디자인 (글씨 흰색 강제 적용) */
    .result-box {
        padding: 25px; 
        border-radius: 12px; 
        margin: 15px 0; 
        border: 1px solid #555;
        color: #e0e0e0 !important; /* 기본 글씨 밝은 회색 */
        line-height: 1.6;
        font-size: 1.05em;
    }
    
    /* 제목, 강조 텍스트는 완전 흰색으로 */
    .result-box h1, .result-box h2, .result-box h3, .result-box strong, .result-box b {
        color: #ffffff !important;
        font-weight: 700;
    }

    /* 상태별 배경색 */
    .res-stop {background-color: #2d1212; border-left: 6px solid #ff4b4b;} 
    .res-mod {background-color: #2d240b; border-left: 6px solid #ffa425;}
    .res-go {background-color: #0f2615; border-left: 6px solid #00cc44;}

    /* 카카오톡 템플릿 영역 */
    .kakao-area {
        background-color: #383838;
        padding: 15px;
        border-radius: 8px;
        margin-top: 10px;
        border: 1px dashed #777;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 핵심 유틸리티
# -----------------------------------------------------------------------------
def get_korea_timestamp():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

def extract_kakao_message(full_text):
    try:
        # 정규식으로 카톡 템플릿 부분만 추출
        match = re.search(r"3\. 💬 카카오톡 전송 템플릿\s*-+\s*(.*?)\s*-+", full_text, re.DOTALL)
        if match: return match.group(1).strip()
        # 실패 시 전체 텍스트 중 일부 반환
        return full_text[:100]
    except: return full_text[:100]

def connect_db():
    try:
        if "gcp_service_account" not in st.secrets: return None, "Secrets 설정 누락"
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        return client.open("MAP_DATABASE").sheet1, "✅ 연결 성공"
    except Exception as e: return None, str(e)

def send_kakao_message(text):
    try:
        if "KAKAO_TOKEN" not in st.secrets: return False, "토큰 없음"
        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        headers = {"Authorization": "Bearer " + st.secrets["KAKAO_TOKEN"]}
        data = {"template_object": str({"object_type": "text", "text": text, "link": {"web_url": "https://streamlit.io"}})}
        res = requests.post(url, headers=headers, data=data)
        return (True, "성공") if res.status_code == 200 else (False, f"실패({res.status_code})")
    except Exception as e: return False, str(e)

def safe_append_row(sheet, row):
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e: return False, str(e)

# -----------------------------------------------------------------------------
# 3. 사이드바 & 초기화
# -----------------------------------------------------------------------------
st.sidebar.title("🔧 MAP Admin Console")
sheet, db_msg = connect_db()
if sheet: st.sidebar.success(db_msg)
else: st.sidebar.error(db_msg)

if "OPENAI_API_KEY" in st.secrets:
    ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    ai_client = None

# -----------------------------------------------------------------------------
# 4. 프롬프트 (CORE v2026 - 절대 잘리지 않게 전체 복사하세요!)
# -----------------------------------------------------------------------------
MAP_CORE_PROMPT = """
# MASTER SYSTEM: MAP_INTEGRATED_CORE_v2026 (LITE)
# PRIORITY: Legal Safety > Operational Structure > Member Care

**[SYSTEM ROLE]**
Non-medical administrative safety system protecting Center/Trainer/Owner.
Ensures members feel "managed" via structure/records, not emotion.

**[ABSOLUTE RULES]**
1. LEGAL FIRST: Operational protection is priority #1.
2. CARE BY STRUCTURE: Care comes from consistency, not sentiment.
3. NO PSYCHOLOGY: Do not perform persuasion, empathy, or therapy.

**[OUTPUT FORMATS]**
You MUST output the response in the following structured sections using Markdown:

### 1. 📋 FSL 현장 리포트
---
**[MAP ANALYSIS : {Timestamp}]**
**Target:** {Client_Tag}
**Plan:** {Exercise_Summary}

**1. 판정:** [GO] or [MODIFICATION] or [STOP]
※ 본 시스템은 의사결정 보조용 기록 시스템이며, 실제 운동 진행 여부에 대한 판단과 책임은 현장 트레이너에게 있습니다.

**2. 리스크 요인:**
- (Explain strictly in 1 sentence)

**3. 액션 프로토콜:**
- ⛔ **제한:** (Specific restriction)
- ✅ **대체:** (Alternative exercise)
- ⚠️ **큐잉:** (Safety cue)
---

### 2. 🔬 MAP 상세 분석 로그
---
**Red Flag Check:** (Pass/Fail)
**Mechanism Check:** (Detail)
**Sanitization:** (Masked)
---

### 3. 💬 카카오톡 전송 템플릿
---
안녕하세요, {Client_Tag}님.
**MAP 트레이닝 센터**입니다.

오늘 컨디션(증상 요약)을 고려하여, 안전을 최우선으로 한 맞춤 가이드를 준비했습니다.

📌 **오늘의 운동 포인트**
: (Write a polite, safe guideline sentence here based on the decision)

현장에서 트레이너와 함께 안전하게 진행해요! 💪
(본 안내는 운동 안전 참고 자료이며 의료적 판단이 아닙니다.)
---
"""

# -----------------------------------------------------------------------------
# 5. 메인 UI (여기까지 다 복사해야 합니다!)
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.caption("CORE v2026 | Governance Engine Active")
st.write(f"🕒 Time (KST): {get_korea_timestamp()}")

tab1, tab2 = st.tabs(["🧬 PT 안전 분류 (Safety)", "🏢 시설 관리 로그"])

# === [TAB 1] PT 안전 분류 ===
with tab1:
    with st.form("pt_form"):
        c1, c2 = st.columns(2)
        with c1:
            member = st.text_input("회원 정보", placeholder="예: 50대 남성, 허리디스크")
            symptom = st.text_input("현재 상태", placeholder="예: 오늘 허리 통증")
        with c2:
            exercise = st.text_input("예정 운동", placeholder="예: 데드리프트")
            
        send_k = st.checkbox("결과를 카톡으로 전송", value=True)
        btn = st.form_submit_button("⚡ CORE 엔진 분석 실행")

    if btn:
        if ai_client and sheet:
            with st.spinner("⚖️ MAP CORE v2026 엔진이 프로토콜을 분석 중입니다..."):
                try:
                    # 프롬프트 조립
                    final_prompt = MAP_CORE_PROMPT.format(
                        Timestamp=get_korea_timestamp(),
                        Client_Tag=member,
                        Exercise_Summary=exercise
                    )
                    final_prompt += f"\n\n[INPUT DATA]\nMember: {member}\nSymptom: {symptom}\nExercise: {exercise}\n\nAnalyze now."

                    # AI 요청
                    response = ai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": final_prompt}],
                        temperature=0.2
                    )
                    full_res = response.choices[0].message.content

                    # 화면 출력 (색상 적용)
                    if "[STOP]" in full_res: css_class = "res-stop"
                    elif "[MODIFICATION]" in full_res: css_class = "res-mod"
                    else: css_class = "res-go"
                    
                    st.markdown(f"<div class='result-box {css_class}'>{full_res}</div>", unsafe_allow_html=True)

                    # 카톡 추출 및 DB 저장
                    kakao_msg = extract_kakao_message(full_res)
                    ok, _ = safe_append_row(sheet, [
                        get_korea_timestamp(), "PT_CORE_ANALYSIS", member, symptom, exercise, "DONE", full_res[:4000]
                    ])
                    
                    if ok:
                        st.success("💾 MAP 리포트 저장 완료")
                        if send_k:
                            k_ok, k_err = send_kakao_message(kakao_msg)
                            if k_ok: 
                                st.toast("💬 카톡 전송 완료!")
                                with st.expander("보낸 카톡 내용 보기"):
                                    st.text(kakao_msg)
                            else: st.warning(f"카톡 실패: {k_err}")
                    else:
                        st.error("DB 저장 실패")

                except Exception as e: st.error(f"엔진 오류: {e}")

# === [TAB 2] 시설 관리 ===
with tab2:
    st.subheader("🛠️ 시설 안전 점검 로그")
    with st.form("fac_form"):
        task = st.selectbox("점검 유형", ["오픈조 순찰", "마감조 순찰", "기구 정비"])
        place = st.selectbox("구역", ["웨이트존", "유산소존", "샤워실"])
        memo = st.text_input("특이사항", "이상 없음")
        staff = st.text_input("점검자")
        send_k_fac = st.checkbox("점검 완료 카톡 보고", value=True)
        save = st.form_submit_button("로그 저장")

    if save:
        if sheet:
            ok, err = safe_append_row(sheet, [get_korea_timestamp(), "FACILITY", task, place, memo, staff])
            if ok:
                st.success(f"✅ [{task}] 저장 완료")
                if send_k_fac:
                    msg = f"[시설 점검 보고]\n시간: {get_korea_timestamp()}\n점검자: {staff}\n유형: {task}\n특이사항: {memo}"
                    send_kakao_message(msg)
            else: st.error(f"저장 실패: {err}")
