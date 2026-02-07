import streamlit as st
import openai
from datetime import datetime

# 1. 기본 설정
st.set_page_config(page_title="MAP SAFETY SYSTEM", page_icon="🛡️")

# API 키 설정
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("🚨 SYSTEM ERROR: API Key is missing. Please check Streamlit Secrets.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# 2. 시스템 프롬프트 (SMART-LITE) - [지능형 뇌 장착 완료]
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
- Do NOT output internal logic or reasoning steps.
- Generate User Name if missing ('User_' + hash).

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
안녕하세요, {Generated_Name}님.
**MAP 트레이닝 센터**입니다.

오늘 컨디션({Risk_Summary_Text})을 고려하여, 안전을 최우선으로 한 맞춤 가이드를 준비했습니다.

📌 **오늘의 운동 포인트**
: {Kakao_Sentence_Text}

현장에서 트레이너와 함께 안전하게 진행해요! 💪
(본 안내는 운동 안전 참고 자료입니다.)
---
"""

# 3. 헤더
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.markdown("**Status:** `OPERATIONAL` 🟢 | **Mode:** `SAFETY_LOG` 📝")

# 4. 탭 구성
tab1, tab2 = st.tabs(["🏋️ PT 컨디션 체크 (회원용)", "🚨 시설 안전 점검 (직원용)"])

# ==========================================
# [TAB 1] PT 수업 전 컨디션 체크 (AI 엔진 가동)
# ==========================================
with tab1:
    st.subheader("1:1 PT 수업 가이드")
    st.caption("수업 전 회원의 컨디션을 체크하여 안전한 가이드를 생성합니다.")
    
    with st.form("pt_form"):
        member_info = st.text_input("1. 회원 정보", placeholder="예: 남/50대/디스크")
        symptom = st.text_input("2. 현재 증상", placeholder="예: 허리 통증")
        exercise = st.text_input("3. 예정 운동", placeholder="예: 데드리프트")
        submitted_pt = st.form_submit_button("🛡️ 가이드 생성")

    if submitted_pt:
        if not member_info or not symptom or not exercise:
            st.warning("⚠️ 모든 항목을 입력해주세요.")
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
                    st.success("분석 완료")
                    st.markdown(response.choices[0].message.content)
                    st.info("👆 위 내용을 복사하여 회원 카톡으로 전송하세요.")
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# [TAB 2] MAP FACILITY - COURT READY VER. (법적 무결성 버전)
# ==========================================
with tab2:
    st.subheader("⚠️ 시설 안전 점검 로그")
    st.caption("※ 본 기록은 사고 발생 시 센터의 '관리 의무 이행'을 입증하는 자료입니다.")

    with st.form("facility_form"):
        # 1. 작업 유형 (용어 순화: Protocol -> Task)
        task_type = st.radio("점검 유형", 
            ["🔄 정기 순찰 (Routine Patrol)", 
             "🎓 신규/안전 교육 (Safety OT)", 
             "🛠️ 기구 정비 (Maintenance)"])
        
        # 2. 타겟 구역
        target_zone = st.selectbox("점검 구역", 
            ["ZONE A (유산소/런닝머신)", "ZONE B (프리웨이트)", "ZONE C (머신존)", "ZONE D (탈의실/샤워실)"])
        
        st.markdown("---")
        st.markdown("**✅ 현장 확인 항목 (Physical Check)**")
        
        # 3. 상황별 동적 체크리스트 (함정 제거 완료)
        chk_1, chk_2 = False, False
        
        if "정기 순찰" in task_type:
            # 순찰: 사람에게 말 걸지 않음. 시설만 봄. (위증 위험 제거)
            chk_1 = st.checkbox("기구 상태: 전원/비상정지/케이블 정상")
            chk_2 = st.checkbox("환경 상태: 바닥 물기/장애물/청결 확인")
            st.caption("※ 순찰 중에는 시설물의 물리적 상태 위주로 점검하십시오.")
            
        elif "신규/안전 교육" in task_type:
            # OT: 이때만 '사람'에게 경고함.
            chk_1 = st.checkbox("위험 고지: 비상정지 및 부상 위험 설명 완료")
            chk_2 = st.checkbox("시연 확인: 올바른 사용법 시연 및 회원 인지 확인")
            st.caption("※ 반드시 회원에게 구두 설명 후 체크하십시오.")
            
        elif "기구 정비" in task_type:
            chk_1 = st.checkbox("조치 내용: 고장 부위 수리/부품 교체")
            chk_2 = st.checkbox("작동 테스트: 수리 후 정상 작동 확인")
        
        # 4. 수행자 (용어 순화: Actuator -> Staff)
        st.markdown("---")
        staff_name = st.text_input("점검자 실명 (Staff Name)", placeholder="예: 홍길동")
        
        # 5. 실행 버튼 (용어 순화: Execute -> Save Log)
        submitted_facility = st.form_submit_button("💾 안전 점검 로그 저장")

    # [최종: 법정 대응용 '건조한' 로그 생성]
    if submitted_facility:
        if not staff_name:
            st.warning("⚠️ 점검자 실명을 입력해주세요.")
        elif not (chk_1 or chk_2):
             st.warning("⚠️ 최소 1개 이상의 항목을 확인해야 합니다.")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # GPT 피드백 반영: '검증됨' 삭제 -> 'FACT' 나열
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
            task_code = task_type.split(' (')[1].replace(')', '') # 괄호 안 영문만 추출

            # 변호사가 가장 좋아하는 '재미없는 로그' 포맷
            log_text = f"""
            [FACILITY SAFETY LOG]
            -----------------------------------------
            EVENT      : {task_code}
            TIMESTAMP  : {now}
            LOCATION   : {target_zone.split(' (')[0]}
            ACTION     : {formatted_check}
            STAFF      : {staff_name}
            -----------------------------------------
            """
            st.success("✅ 안전 점검 기록이 저장되었습니다.")
            st.code(log_text, language='yaml')
            st.caption("위 로그를 복사하여 업무일지/단톡방에 전송하십시오.")
