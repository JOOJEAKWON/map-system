import streamlit as st
import openai

# 1. 페이지 설정
st.set_page_config(page_title="MAP SYSTEM", page_icon="🛡️")

# 2. 제목 및 안내
st.title("🛡️ MAP SYSTEM (LITE)")
st.info("수업 전 회원의 상태를 입력하면 안전 가이드가 생성됩니다.")

# 3. API 키 설정 (Secrets에서 불러오기)
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    st.error("API 키가 설정되지 않았습니다. [Settings] > [Secrets]에 키를 등록해주세요.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# 4. 입력 폼 (트레이너용)
with st.form("map_input_form"):
    member_info = st.text_input("1. 회원 정보", placeholder="예: 남/50대/디스크 과거력")
    symptom = st.text_input("2. 현재 증상", placeholder="예: 허리 통증, 다리 저림")
    exercise = st.text_input("3. 예정 운동", placeholder="예: 데드리프트, 스쿼트")
    
    submitted = st.form_submit_button("🛡️ MAP 분석 시작")

# 5. 시스템 프롬프트 (LITE 버전)
SYSTEM_PROMPT = """
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
- No exercise prescriptions (only admin classifications).

**[OUTPUT TYPES]**
Type 2: Safety Report (GO / MODIFICATION / STOP)
Type 6: RED FLAG

**[LOGIC MODULES]**
- RED FLAG: Chest/Radiating pain, Shortness of breath, Fainting, Paralysis, Speech issues, Severe headache → Type 6 IMMED.
- STANDARD:
  1. High-risk pain OR Pain+Limit → STOP
  2. Mechanism conflict → MODIFICATION
  3. Else → GO

**[OUTPUT FORMATS]**

**[Type 2: REPORT]**
### 1. 📋 FSL 현장 리포트
---
[MAP ANALYSIS]
Target: {Client_Tag} | Plan: {Exercise_Summary}

**1. 판정:** [{Decision}]
※ 본 시스템은 의사결정 보조용 기록 시스템이며, 실제 운동 진행 여부에 대한 판단과 책임은 현장 트레이너에게 있습니다.

**2. 리스크 요인:**
- {Risk_Summary}

**3. 액션 프로토콜:**
- ⛔ 제한: {Limit}
- ✅ 대체: {Alternative}
- ⚠️ 큐잉: {Cue}
---

### 3. 💬 카카오톡 전송 템플릿
---
안녕하세요, {Client_Tag}님.
**MAP 트레이닝 센터**입니다.

오늘 컨디션({Risk_Summary})을 고려하여, 안전을 최우선으로 한 맞춤 가이드를 준비했습니다.

📌 **오늘의 운동 포인트**
: {Kakao_Sentence}

현장에서 트레이너와 함께 안전하게 진행해요! 💪
(본 안내는 운동 안전 참고 자료이며 의료적 판단이 아닙니다.)
---
"""

# 6. 실행 및 출력
if submitted:
    if not member_info or not symptom or not exercise:
        st.warning("⚠️ 3가지 항목을 모두 입력해주세요.")
    else:
        with st.spinner("MAP 엔진이 분석 중입니다..."):
            try:
                # 사용자 입력 조합
                user_input = f"1. 회원정보: {member_info}\n2. 현재증상: {symptom}\n3. 예정운동: {exercise}"
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.7
                )
                
                result = response.choices[0].message.content
                
                # 결과 출력
                st.success("분석 완료!")
                st.markdown(result)
                st.caption("위 내용을 복사하여 카카오톡으로 전송하세요.")
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
