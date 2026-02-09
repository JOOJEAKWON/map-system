import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import re

# -----------------------------------------------------------------------------
# 1. 시스템 설정 & 라이트 모드(Clean White) 스타일링
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    /* 1. 전체 배경 및 기본 폰트 (흰색 배경, 검은 글씨) */
    .main {
        background-color: #FFFFFF;
        color: #333333;
    }
    
    /* 2. 입력 폼 디자인 (깔끔한 화이트 카드) */
    .stForm {
        background-color: #F8F9FA; /* 아주 연한 회색 */
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E0E0E0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* 3. 결과 박스 디자인 (가독성 최적화) */
    .result-box {
        padding: 25px; 
        border-radius: 12px; 
        margin-top: 20px; 
        margin-bottom: 20px;
        border: 1px solid #ddd;
        line-height: 1.6;
        font-size: 1.1em;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    /* 제목 및 강조 텍스트 (진한 검정) */
    .result-box h1, .result-box h2, .result-box h3, .result-box strong {
        color: #111111 !important;
        font-weight: 800;
    }

    /* 4. 상태별 컬러 테마 (파스텔 톤 배경 + 진한 글씨) */
    /* STOP: 연한 빨강 배경 + 진한 빨강 글씨 */
    .res-stop {
        background-color: #FFF0F0; 
        border-left: 8px solid #FF4B4B;
        color: #8B0000 !important;
    } 
    /* MODIFICATION: 연한 주황 배경 + 진한 주황 글씨 */
    .res-mod {
        background-color: #FFF8E1; 
        border-left: 8px solid #FFA500;
        color: #8B4500 !important;
    }
    /* GO: 연한 초록 배경 + 진한 초록 글씨 */
    .res-go {
        background-color: #E8F5E9; 
        border-left: 8px solid #00C853;
        color: #1B5E20 !important;
    }

    /* 5. 카카오톡 영역 (노란색 강조) */
    .kakao-area {
        background-color: #FEE500;
        color: #3b1e1e !important;
        padding: 15px;
        border-radius: 10px;
        margin-top: 15px;
        font-weight: bold;
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
        match = re.search(r"3\. 💬 카카오톡 전송 템플릿\s*-+\s*(.*?)\s*-+", full_text, re.DOTALL)
        if match: return match.group(1).strip()
        return full_text[:100]
    except: return full_text[:100]

def connect_db():
    try:
        if "gcp_service_account" not in st.secrets: return None, "Secrets 설정 누락"
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        return client.open("MAP_DATABASE").sheet1, "✅ DB 연결됨"
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
# 3. 사이드바 (상태 모니터링)
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 📡 SYSTEM STATUS")
sheet, db_msg = connect_db()
if sheet: st.sidebar.success(db_msg)
else: st.sidebar.error(db_msg)

if "OPENAI_API_KEY" in st.secrets:
    ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    ai_client = None

# -----------------------------------------------------------------------------
# 4. 프롬프트 (CORE v2026 - 유지)
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
# 5. 메인 UI (Clean White Theme)
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.write(f"🕒 Time (KST): **{get_korea_timestamp()}**")

tab1, tab2 = st.tabs(["🧬 PT 안전 분류 (Safety)", "🏢 시설 관리 로그"])

# === [TAB 1] PT 안전 분류 ===
with tab1:
    with st.container():
        st.markdown("### 📋 PT 세션 안전 점검")
        with st.form("pt_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**👤 회원 정보**")
                member = st.text_input("회원 특이사항", placeholder="예: 50대 남성, 허리디스크")
                
                st.markdown("**🩺 컨디션 체크**")
                body_part = st.selectbox("주요 통증/불편 부위 (빠른 선택)", 
                                       ["없음 (양호)", "허리 (Lumbar)", "무릎 (Knee)", "어깨 (Shoulder)", "목 (Neck)", "손목/발목", "직접 입력"])
                
                detail_symptom = ""
                if body_part == "직접 입력":
                    detail_symptom = st.text_input("증상 상세 입력", placeholder="구체적인 증상을 적어주세요")
                elif body_part != "없음 (양호)":
                    detail_symptom = body_part + " 통증/불편감"
                else:
                    detail_symptom = "특이사항 없음"

            with col2:
                st.markdown("**🏋️ 운동 계획**")
                exercise = st.text_input("수행 예정 운동", placeholder="예: 데드리프트, 스쿼트")
                
                st.markdown("**📨 옵션**")
                send_k = st.checkbox("✅ 결과를 카카오톡으로 전송", value=True)
                
            st.divider()
            btn = st.form_submit_button("🚀 CORE 엔진 분석 실행", use_container_width=True)

    if btn:
        if ai_client and sheet:
            final_symptom = detail_symptom
            
            with st.status("🧠 분석 중...", expanded=True) as status:
                try:
                    status.write("🔍 데이터 파싱 중...")
                    final_prompt = MAP_CORE_PROMPT.format(
                        Timestamp=get_korea_timestamp(),
                        Client_Tag=member,
                        Exercise_Summary=exercise
                    )
                    final_prompt += f"\n\n[INPUT DATA]\nMember: {member}\nSymptom: {final_symptom}\nExercise: {exercise}\n\nAnalyze now."

                    status.write("⚖️ 리스크 계산 중...")
                    response = ai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": final_prompt}],
                        temperature=0.2
                    )
                    full_res = response.choices[0].message.content
                    
                    status.write("💾 데이터베이스 기록 중...")
                    kakao_msg = extract_kakao_message(full_res)
                    ok, _ = safe_append_row(sheet, [
                        get_korea_timestamp(), "PT_CORE_ANALYSIS", member, final_symptom, exercise, "DONE", full_res[:4000]
                    ])
                    
                    if ok:
                        status.update(label="✅ 분석 및 저장 완료!", state="complete", expanded=False)
                        
                        if "[STOP]" in full_res: css_class = "res-stop"
                        elif "[MODIFICATION]" in full_res: css_class = "res-mod"
                        else: css_class = "res-go"
                        
                        st.markdown(f"<div class='result-box {css_class}'>{full_res}</div>", unsafe_allow_html=True)

                        if send_k:
                            k_ok, k_err = send_kakao_message(kakao_msg)
                            if k_ok: st.success("💬 카톡 전송 완료!")
                            else: st.warning(f"카톡 실패: {k_err}")
                    else:
                        status.update(label="❌ DB 저장 실패", state="error")
                        st.error("데이터베이스 저장 실패")

                except Exception as e: 
                    status.update(label="❌ 시스템 오류", state="error")
                    st.error(f"엔진 오류: {e}")

# === [TAB 2] 시설 관리 (간소화 버전) ===
with tab2:
    with st.container():
        st.markdown("### 🛠️ 시설 안전 점검 로그")
        
        with st.form("fac_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # [수정] 불필요한 오픈/마감조 삭제 -> 행위 위주로 변경
                task = st.radio("작업 유형", ["시설 순찰 (Patrol)", "기구 정비 (Fix)", "청소/환경 (Clean)", "기타 조치"], horizontal=True)
                place = st.radio("점검 구역", ["웨이트존", "유산소존", "탈의실/샤워장", "프리웨이트/GX"], horizontal=True)
            
            with col2:
                memo = st.text_input("특이사항 / 조치내용", "이상 없음 (Clear)")
                staff = st.text_input("점검자 서명 (Staff Name)")
                send_k_fac = st.checkbox("지점장님께 카톡 보고", value=True)
            
            st.divider()
            save = st.form_submit_button("📝 점검 기록 저장", use_container_width=True)

    if save:
        if sheet:
            if not staff:
                st.warning("⚠️ 점검자 이름을 입력해주세요.")
            else:
                ok, err = safe_append_row(sheet, [get_korea_timestamp(), "FACILITY", task, place, memo, staff])
                if ok:
                    st.success(f"✅ [{task}] 저장 완료")
                    if send_k_fac:
                        msg = f"[시설 점검 보고]\n시간: {get_korea_timestamp()}\n점검자: {staff}\n유형: {task}\n특이사항: {memo}"
                        send_kakao_message(msg)
                else: st.error(f"저장 실패: {err}")
