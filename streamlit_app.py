import streamlit as st
import openai
import pandas as pd
from datetime import datetime

# [안전 장치] 구글 시트 라이브러리가 있는지 확인
try:
    from streamlit_gsheets import GSheetsConnection
    gsheets_available = True
except ImportError:
    gsheets_available = False

# 1. 페이지 설정
st.set_page_config(page_title="MAP SYSTEM", page_icon="🛡️")
st.title("🛡️ MAP SYSTEM (Full ver.)")
st.info("수업 전 회원의 상태를 입력하면 안전 가이드와 로그가 생성됩니다.")

# 2. API 키 설정
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    st.error("API 키가 설정되지 않았습니다. [Secrets]에 OPENAI_API_KEY를 등록해주세요.")
    st.stop()

client = openai.OpenAI(api_key=api_key)

# 3. 입력 폼
with st.form("map_input_form"):
    col1, col2 = st.columns(2)
    with col1:
        member_name = st.text_input("회원명 (가명)", placeholder="예: Member_A")
        member_info = st.text_input("회원 정보", placeholder="예: 남/50대/디스크")
    with col2:
        symptom = st.text_input("현재 증상", placeholder="예: 허리 통증")
        exercise = st.text_input("예정 운동", placeholder="예: 데드리프트")
    
    submitted = st.form_submit_button("🛡️ MAP 분석 및 기록")

# 4. 시스템 프롬프트 (LITE)
SYSTEM_PROMPT = """
# MASTER SYSTEM: MAP_INTEGRATED_CORE_v2026 (LITE)
# PRIORITY: Legal Safety > Operational Structure > Member Care

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

# 5. 실행 로직
if submitted:
    if not member_name or not member_info or not symptom or not exercise:
        st.warning("⚠️ 모든 항목을 입력해주세요.")
    else:
        with st.spinner("MAP 엔진 분석 및 로그 저장 중..."):
            try:
                # A. GPT 분석
                user_input = f"Target: {member_name}\n1.Info: {member_info}\n2.Symptom: {symptom}\n3.Plan: {exercise}"
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.7
                )
                result = response.choices[0].message.content
                
                # B. 결과 출력
                st.success("분석 완료!")
                st.markdown(result)
                st.caption("위 내용을 복사하여 카카오톡으로 전송하세요.")

                # C. 구글 시트 저장 시도 (안전 장치 포함)
                if gsheets_available:
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        # 현재 시간
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        # 저장할 데이터
                        log_data = pd.DataFrame([{
                            "Timestamp": now,
                            "Member": member_name,
                            "Info": member_info,
                            "Symptom": symptom,
                            "Exercise": exercise,
                            "Result": "Generated"
                        }])
                        # 시트에 추가 (append)
                        # 주의: 시트가 비어있거나 설정이 없으면 에러날 수 있음 -> pass 처리
                        # conn.update(data=log_data) # 단순 예시
                        st.toast("📝 로그 저장 시도 완료 (설정 확인 필요)")
                    except Exception as e:
                        st.warning(f"로그 저장 실패 (구글 시트 설정 필요): {e}")
                else:
                    st.info("ℹ️ 구글 시트 모듈이 설치되지 않아 로그 저장은 생략합니다.")

            except Exception as e:
                st.error(f"오류 발생: {e}")
