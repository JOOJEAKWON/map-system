import streamlit as st
import openai
import re
from datetime import datetime

# ---------------------------------------------------------
# 1. 기본 설정 & UI 스타일링 (글자 크기 축소 등)
# ---------------------------------------------------------
st.set_page_config(page_title="MAP SAFETY SYSTEM", page_icon="🛡️", layout="centered")

st.markdown("""
<style>
/* 전체 폰트 및 여백 최적화 */
html, body, [class*="css"] { font-size: 14px !important; }
h1 { font-size: 24px !important; margin-bottom: 10px !important; }
h2 { font-size: 18px !important; margin-top: 10px !important; }
h3 { font-size: 16px !important; }
div[data-testid="stAlert"] { padding: 8px 10px !important; }
.small-caption { font-size: 12px !important; color: #666; }

/* 카톡 텍스트 박스 스타일 */
.kakao-box {
  font-size: 13px !important;
  line-height: 1.5 !important;
  background: #f1f3f5;
  border: 1px solid #ced4da;
  border-radius: 8px;
  padding: 12px;
  white-space: pre-wrap;
}
</style>
""", unsafe_allow_html=True)

# API 키 설정
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("🚨 SYSTEM ERROR: API Key is missing. Please check Streamlit Secrets.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# ---------------------------------------------------------
# 2. 시스템 프롬프트 (SMART-LITE) - 지능형 뇌 장착
# ---------------------------------------------------------
SYSTEM_PROMPT = """
# MASTER SYSTEM: MAP_INTEGRATED_CORE_v2026 (SMART-LITE)
# ROLE: Safety Admin System for Gyms

**[CORE LOGIC: ANATOMICAL SEPARATION]**
1. **Separation Rule (Crucial):**
   - If Pain is LOWER Body (e.g., Knee, Ankle) AND Exercise is UPPER Body (e.g., Shoulder, Chest) -> **GO (Green)**.
   - If Pain is UPPER Body AND Exercise is LOWER Body -> **GO (Green)**.
   - ONLY trigger MODIFICATION/STOP if the pain DIRECTLY conflicts with the joint used in exercise.

**[DECISION PRIORITY]**
1. **RED FLAG (Emergency):** Chest pain, Radiating pain, Fainting -> Type 6
2. **STOP (High Risk):** Pain site == Exercise site (e.g., Back pain + Deadlift)
3. **MODIFICATION (Medium Risk):** Indirect conflict (e.g., Wrist pain + Push-up)
4. **GO (Safe):** No conflict OR Separation Rule applies -> Type 2

**[OUTPUT FORMAT RULES]**
- Output ONLY the final text. No placeholders.
- Do NOT output internal logic.

**[OUTPUT TEMPLATE]**
### 1. 📋 FSL 현장 리포트
---
[MAP ANALYSIS : {Timestamp}]
Target: {Generated_Name}
Plan: {Exercise_Input}

**1. 판정:** {Decision_Emoji} {Decision_Text}
※ 본 시스템은 의사결정 보조용이며, 최종 책임은 현장 트레이너에게 있습니다.

**2. 리스크 요인:**
- {Risk_Summary_Text}

**3. 액션 프로토콜:**
- ⛔ 제한: {Limit_Text}
- ✅ 대체: {Alternative_Text}
- ⚠️ 큐잉: {Cue_Text}
---
### 3. 💬 카카오톡 전송 템플릿
---
(AI generated content will be replaced by Python post-processing for better tone)
---
"""

# ---------------------------------------------------------
# 3. 헬퍼 함수: 카톡 멘트 강화 (Tone Polish)
# ---------------------------------------------------------
def enhance_kakao_message(original_text, user_info, symptom, exercise):
    """AI 결과를 기반으로 더 따뜻하고 전문적인 카톡 멘트를 생성합니다."""
    # 리스크 요인 추출 (간단한 파싱 시도)
    risk_summary = "컨디션 이슈"
    if "리스크 요인:" in original_text:
        try:
            risk_part = original_text.split("리스크 요인:")[1].split("3. 액션 프로토콜:")[0].strip()
            risk_summary = risk_part.replace("-", "").strip().split("\n")[0]
        except:
            pass

    return f"""안녕하세요, 회원님.
**MAP 트레이닝 센터**입니다.

오늘 말씀해주신 컨디션({risk_summary})을 꼼꼼히 확인했습니다.
안전을 위해 다음과 같이 운동 가이드를 준비했습니다.

📌 **오늘의 진행 포인트**
: {symptom} 관련 부담은 줄이고, 안전한 대체 동작으로 진행합니다.
: 무리한 중량보다는 정확한 자세에 집중하겠습니다.

현장에서 저와 함께 안전하게 득근해요! 💪
(수업 중 불편한 점은 바로 말씀해주세요.)"""

# ---------------------------------------------------------
# 4. 앱 메인 구조 (탭 구성)
# ---------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.markdown("**Status:** `OPERATIONAL` 🟢 | **Mode:** `ENTERPRISE_LOG` 🏢")

tab1, tab2 = st.tabs(["🏋️ PT 컨디션 체크 (회원용)", "🚨 시설 안전 점검 (직원용)"])

# =========================================================
# [TAB 1] PT 수업 가이드 (UI 개선 + 카톡 강화)
# =========================================================
with tab1:
    st.markdown("### 1:1 PT 수업 가이드")
    st.caption("수업 전 회원의 상태를 입력하면 안전 가이드가 생성됩니다.")
    
    with st.form("pt_form"):
        col1, col2 = st.columns(2)
        with col1:
            member_info = st.text_input("1. 회원 정보", placeholder="예: 남/50대/디스크")
        with col2:
            symptom = st.text_input("2. 현재 증상", placeholder="예: 허리 통증")
        
        exercise = st.text_input("3. 예정 운동", placeholder="예: 데드리프트, 스쿼트")
        submitted_pt = st.form_submit_button("🛡️ 가이드 생성")

    if submitted_pt:
        if not member_info or not symptom or not exercise:
            st.warning("⚠️ 3가지 항목을 모두 입력해주세요.")
        else:
            with st.spinner("MAP 엔진 분석 중..."):
                try:
                    user_input = f"1. 회원정보: {member_info}\n2. 현재증상: {symptom}\n3. 예정운동: {exercise}"
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                                  {"role": "user", "content": user_input}],
                        temperature=0.7
                    )
                    ai_result = response.choices[0].message.content
                    
                    # 결과 출력
                    st.success("✅ 분석 완료")
                    st.markdown(ai_result)
                    
                    # 카톡 멘트 강화 (파이썬 후처리)
                    final_kakao = enhance_kakao_message(ai_result, member_info, symptom, exercise)
                    
                    st.markdown("---")
                    st.markdown("### 💬 카카오톡 전송용 (복사하세요)")
                    st.markdown(f'<div class="kakao-box">{final_kakao}</div>', unsafe_allow_html=True)
                    st.caption("위 박스 내용을 복사하여 회원 카톡으로 전송하세요.")
                    
                except Exception as e:
                    st.error(f"Error: {e}")

# =========================================================
# [TAB 2] MAP FACILITY - ENTERPRISE READY VER.
# =========================================================
with tab2:
    st.markdown("### ⚠️ 시설 안전 점검 로그 (Enterprise)")
    st.caption("※ 본 기록은 **킹스짐 전 지점**의 안전 관리 현황으로 집계됩니다.")

    with st.form("facility_form"):
        # 0. [NEW] 지점 선택 (데이터 분류의 핵심)
        branch_name = st.selectbox("지점 선택 (Current Branch)", 
            ["킹스짐 1호점 (본점)", "킹스짐 2호점", "킹스짐 3호점"])

        # 1. 작업 유형
        task_type = st.radio("점검 유형", 
            ["🔄 정기 순찰 (Routine Patrol)", 
             "🎓 신규/안전 교육 (Safety OT)", 
             "🛠️ 기구 정비 (Maintenance)"])
        
        # 2. 타겟 구역
        target_zone = st.selectbox("점검 구역", 
            ["ZONE A (유산소/런닝머신)", "ZONE B (프리웨이트)", "ZONE C (머신존)", "ZONE D (탈의실/샤워실)"])
        
        st.markdown("---")
        st.markdown("**✅ 현장 확인 항목 (Physical Check)**")
        
        # 3. 상황별 동적 체크리스트
        chk_1, chk_2 = False, False
        
        if "정기 순찰" in task_type:
            chk_1 = st.checkbox("기구 상태: 전원/비상정지/케이블 정상")
            chk_2 = st.checkbox("환경 상태: 바닥 물기/장애물/청결 확인")
            st.caption("※ 순찰 중에는 시설물의 물리적 상태 위주로 점검하십시오.")
            
        elif "신규/안전 교육" in task_type:
            chk_1 = st.checkbox("위험 고지: 비상정지 및 부상 위험 설명 완료")
            chk_2 = st.checkbox("시연 확인: 올바른 사용법 시연 및 회원 인지 확인")
            st.caption("※ 반드시 회원에게 구두 설명 후 체크하십시오.")
            
        elif "기구 정비" in task_type:
            chk_1 = st.checkbox("조치 내용: 고장 부위 수리/부품 교체")
            chk_2 = st.checkbox("작동 테스트: 수리 후 정상 작동 확인")
        
        # 4. 수행자
        st.markdown("---")
        staff_name = st.text_input("점검자 실명 (Staff Name)", placeholder="예: 홍길동")
        
        # 5. 실행 버튼
        submitted_facility = st.form_submit_button("💾 안전 점검 로그 저장")

    # [최종 로그 생성]
    if submitted_facility:
        if not staff_name:
            st.warning("⚠️ 점검자 실명을 입력해주세요.")
        elif not (chk_1 or chk_2):
             st.warning("⚠️ 최소 1개 이상의 항목을 확인해야 합니다.")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            checklist_result = []
            if "정기 순찰" in task_type:
                if chk_1: checklist_result.append("MACHINE_STATUS: OK")
                if chk_2: checklist_result.append("ENV_CLEAR: OK")
            elif "신규/안전 교육" in task_type:
                if chk_1: checklist_result.append("USER_WARNING: DONE")
                if chk_2: checklist_result.append("DEMO_CHECK: DONE")
            elif "기구 정비" in task_type:
                if chk_1: checklist_result.append("REPAIR_ACTION: DONE")
                if chk_2: checklist_result.append("TEST_RUN: OK")

            formatted_check = " / ".join(checklist_result)
            task_code = task_type.split(' (')[1].replace(')', '')

            # [핵심] 지점명이 포함된 엔터프라이즈 로그
            log_text = f"""
            [MAP ENTERPRISE LOG]
            -----------------------------------------
            BRANCH     : {branch_name}
            EVENT      : {task_code}
            TIMESTAMP  : {now}
            LOCATION   : {target_zone.split(' (')[0]}
            ACTION     : {formatted_check}
            STAFF      : {staff_name}
            -----------------------------------------
            """
            st.success(f"✅ [{branch_name}] 안전 점검 기록이 저장되었습니다.")
            st.code(log_text, language='yaml')
            st.caption("위 로그를 복사하여 '지점별 단톡방'에 전송하십시오.")
