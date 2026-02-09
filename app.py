import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import re # 텍스트 추출용

# -----------------------------------------------------------------------------
# 1. 시스템 설정 & 스타일 (CORE v2026 디자인)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .main {background-color: #0E1117;}
    .status-badge {padding: 5px 10px; border-radius: 5px; font-weight: bold; color: white;}
    .result-box {padding: 20px; border-radius: 10px; margin: 15px 0; border: 1px solid #444;}
    .res-stop {background: #3a1c1c; border-left: 5px solid #cf1322;} 
    .res-mod {background: #3a2e0e; border-left: 5px solid #d48806;}
    .res-go {background: #0e2a14; border-left: 5px solid #1f7a1f;}
    .report-title {font-size: 1.2em; font-weight: bold; margin-bottom: 10px; color: #eee;}
    .kakao-preview {background: #fae100; color: #3b1e1e; padding: 15px; border-radius: 10px; font-size: 0.9em;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 핵심 유틸리티 (시간, DB, 카톡, 텍스트 파싱)
# -----------------------------------------------------------------------------
def get_korea_timestamp():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

def extract_kakao_message(full_text):
    """AI 답변에서 카카오톡 템플릿 부분만 정교하게 추출"""
    try:
        match = re.search(r"3\. 💬 카카오톡 전송 템플릿\s*-+\s*(.*?)\s*-+", full_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "카톡 메시지 생성 실패 (원문 참조)"
    except:
        return full_text[:100]

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

if st.sidebar.button("DB 연결 테스트"):
    if sheet:
        sheet.append_row([get_korea_timestamp(), "DEBUG", "SYSTEM_CHECK", "OK"])
        st.sidebar.success("테스트 데이터 쓰기 성공")

# -----------------------------------------------------------------------------
# 4. MAP CORE ENGINE PROMPT (가져오신 프롬프트 이식)
# -----------------------------------------------------------------------------
MAP_CORE_PROMPT = """
# MASTER SYSTEM: MAP_INTEGRATED_CORE_v2026 (LITE)
# PRIORITY: Legal Safety > Operational Structure > Member Care

## PART 1: [GOVERNANCE CANON]
**[SYSTEM ROLE]**
Non-medical administrative safety system protecting Center/Trainer/Owner.
Ensures members feel "managed" via structure/records, not emotion.

**[ABSOLUTE RULES]**
1. LEGAL FIRST: Operational protection is priority #1.
2. CARE BY STRUCTURE: Care comes from consistency, not sentiment.
3. NO PSYCHOLOGY: Do not perform persuasion, empathy, or therapy.

**[PROHIBITED]**
- No medical diagnosis, prediction, or advice.
- No explanation of mechanisms/causes.
- No emotional/motivational language.

**[OUTPUT FORMATS]**
You MUST output the response in the following structured sections:

### 1. 📋 FSL 현장 리포트
---
[MAP ANALYSIS : {Timestamp}]
Target: {Client_Tag}
Plan: {Exercise_Summary}

**1. 판정:** [GO] or [MODIFICATION] or [STOP]
※ 본 시스템은 의사결정 보조용 기록 시스템이며, 실제 운동 진행 여부에 대한 판단과 책임은 현장 트레이너에게 있습니다.

**2. 리스크 요인:**
- (Explain strictly in 1 sentence)

**3. 액션 프로토콜:**
- ⛔ 제한: (Specific restriction)
- ✅ 대체: (Alternative exercise)
- ⚠️ 큐잉: (Safety cue)
---

### 2. 🔬 MAP 상세 분석 로그
---
Red Flag Check: (Pass/Fail)
Mechanism Check: (Detail)
Sanitization: (Masked)
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
# 5. 메인 UI
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.caption("CORE v2026 | Governance Engine Active")
st.write(f"🕒 Time (KST): {get_korea_timestamp()}")

tab1, tab2 = st.tabs(["🧬 PT 안전 분류 (Safety)", "🏢 시설 관리 로그"])

# === [TAB 1] PT 안전 분류 (CORE 엔진 적용) ===
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
                    # 프롬프트 조합
                    final_prompt = MAP_CORE_PROMPT.format(
                        Timestamp=get_korea_timestamp(),
                        Client_Tag=member,
                        Exercise_Summary=exercise
                    )
                    final_prompt += f"\n\n[INPUT DATA]\nMember: {member}\nSymptom: {symptom}\nExercise: {exercise}\n\nAnalyze now."

                    # AI 호출
                    response = ai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": final_prompt}],
                        temperature=0.2 # 매우 보수적인 설정
                    )
                    full_res = response.choices[0].message.content

                    # 1. 화면에 리포트 출력
                    # 판정 색상 결정
                    if "[STOP]" in full_res: css_class = "res-stop"
                    elif "[MODIFICATION]" in full_res: css_class = "res-mod"
                    else: css_class = "res-go"
                    
                    st.markdown(f"<div class='result-box {css_class}'>{full_res}</div>", unsafe_allow_html=True)

                    # 2. 카톡 메시지 추출 및 전송
                    kakao_msg = extract_kakao_message(full_res)
                    
                    # 3. DB 저장 (상세 로그는 AI 원문 전체 저장)
                    ok, _ = safe_append_row(sheet, [
                        get_korea_timestamp(), 
                        "PT_CORE_ANALYSIS", 
                        member, 
                        symptom, 
                        exercise, 
                        "ANALYSIS_COMPLETED", 
                        full_res[:4000] # 전체 리포트 저장
                    ])
                    
                    if ok:
                        st.success("💾 MAP 리포트 저장 완료")
                        if send_k:
                            k_ok, k_err = send_kakao_message(kakao_msg)
                            if k_ok: 
                                st.toast("💬 카톡 전송 완료!")
                                with st.expander("보낸 카톡 내용 확인"):
                                    st.text(kakao_msg)
                            else: st.warning(f"카톡 실패: {k_err}")
                    else:
                        st.error("DB 저장 실패")

                except Exception as e: st.error(f"엔진 오류: {e}")

# === [TAB 2] 시설 관리 (기존 유지) ===
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
