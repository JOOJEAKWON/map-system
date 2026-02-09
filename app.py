import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import pandas as pd
import re

# -----------------------------------------------------------------------------
# 1. 시스템 설정 & 스타일
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .main {background-color: #FFFFFF; color: #333;}
    .stForm {background-color: #F8F9FA; padding: 20px; border-radius: 12px; border: 1px solid #E0E0E0;}
    .result-box {padding: 25px; border-radius: 12px; margin: 20px 0; border: 1px solid #ddd; font-size: 1.1em;}
    .result-box h1, .result-box h2, .result-box strong {color: #111 !important;}
    .res-stop {background-color: #FFF0F0; border-left: 8px solid #FF4B4B; color: #8B0000 !important;} 
    .res-mod {background-color: #FFF8E1; border-left: 8px solid #FFA500; color: #8B4500 !important;}
    .res-go {background-color: #E8F5E9; border-left: 8px solid #00C853; color: #1B5E20 !important;}
    
    /* 관리자 통계 카드 디자인 */
    .metric-card {
        background-color: #fff; border: 1px solid #eee; padding: 15px; 
        border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .metric-value {font-size: 2em; font-weight: bold; color: #333;}
    .metric-label {color: #666; font-size: 0.9em;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 유틸리티 함수
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
        requests.post(url, headers=headers, data=data)
        return True, "성공"
    except Exception as e: return False, str(e)

def safe_append_row(sheet, row):
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e: return False, str(e)

# -----------------------------------------------------------------------------
# 3. 사이드바 (로그인 시스템)
# -----------------------------------------------------------------------------
st.sidebar.title("🔐 관리자 접속")

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    password = st.sidebar.text_input("비밀번호 입력", type="password")
    if st.sidebar.button("로그인"):
        # [비밀번호 설정] 원하는 비번으로 바꾸세요 (기본: 1234)
        if password == "1234":  
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.sidebar.error("비밀번호 불일치")
else:
    st.sidebar.success("✅ 관리자 모드 활성화")
    if st.sidebar.button("로그아웃"):
        st.session_state.admin_logged_in = False
        st.rerun()

sheet, db_msg = connect_db()
if not sheet: st.error(f"DB 연결 실패: {db_msg}")

if "OPENAI_API_KEY" in st.secrets:
    ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    ai_client = None

# -----------------------------------------------------------------------------
# 4. 프롬프트 (CORE v2026)
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
# 5. 메인 UI (탭 분기)
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.write(f"🕒 Time (KST): **{get_korea_timestamp()}**")

# 관리자 로그인 여부에 따라 탭 구성 변경
if st.session_state.admin_logged_in:
    tab1, tab2, tab3 = st.tabs(["🧬 PT 안전 분류", "🏢 시설 관리 로그", "👑 관리자 대시보드"])
else:
    tab1, tab2 = st.tabs(["🧬 PT 안전 분류", "🏢 시설 관리 로그"])
    tab3 = None

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
                body_part = st.selectbox("주요 통증/불편 부위", ["없음 (양호)", "허리 (Lumbar)", "무릎 (Knee)", "어깨 (Shoulder)", "목 (Neck)", "손목/발목", "직접 입력"])
                detail_symptom = ""
                if body_part == "직접 입력": detail_symptom = st.text_input("증상 상세 입력")
                elif body_part != "없음 (양호)": detail_symptom = body_part + " 통증/불편감"
                else: detail_symptom = "특이사항 없음"
            with col2:
                st.markdown("**🏋️ 운동 계획**")
                exercise = st.text_input("수행 예정 운동", placeholder="예: 데드리프트")
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
                    final_prompt = MAP_CORE_PROMPT.format(Timestamp=get_korea_timestamp(), Client_Tag=member, Exercise_Summary=exercise)
                    final_prompt += f"\n\n[INPUT DATA]\nMember: {member}\nSymptom: {final_symptom}\nExercise: {exercise}\n\nAnalyze now."
                    
                    status.write("⚖️ 리스크 계산 중...")
                    response = ai_client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": final_prompt}], temperature=0.2)
                    full_res = response.choices[0].message.content
                    
                    status.write("💾 데이터베이스 기록 중...")
                    kakao_msg = extract_kakao_message(full_res)
                    safe_append_row(sheet, [get_korea_timestamp(), "PT_CORE_ANALYSIS", member, final_symptom, exercise, "DONE", full_res[:4000]])
                    
                    status.update(label="✅ 완료!", state="complete", expanded=False)
                    if "[STOP]" in full_res: css = "res-stop"
                    elif "[MODIFICATION]" in full_res: css = "res-mod"
                    else: css = "res-go"
                    st.markdown(f"<div class='result-box {css}'>{full_res}</div>", unsafe_allow_html=True)
                    if send_k: send_kakao_message(kakao_msg)
                except Exception as e: st.error(f"오류: {e}")

# === [TAB 2] 시설 관리 ===
with tab2:
    with st.container():
        st.markdown("### 🛠️ 시설 안전 점검 로그")
        with st.form("fac_form"):
            col1, col2 = st.columns(2)
            with col1:
                task = st.radio("작업 유형", ["시설 순찰 (Patrol)", "기구 정비 (Fix)", "청소/환경 (Clean)", "기타 조치"], horizontal=True)
                place = st.radio("점검 구역", ["웨이트존", "유산소존", "탈의실/샤워장", "프리웨이트/GX"], horizontal=True)
            with col2:
                memo = st.text_input("특이사항", "이상 없음 (Clear)")
                staff = st.text_input("점검자 서명")
                send_k_fac = st.checkbox("지점장님께 카톡 보고", value=True)
            st.divider()
            save = st.form_submit_button("📝 점검 기록 저장", use_container_width=True)

    if save:
        if sheet and staff:
            safe_append_row(sheet, [get_korea_timestamp(), "FACILITY", task, place, memo, staff])
            st.success(f"✅ [{task}] 저장 완료")
            if send_k_fac:
                msg = f"[시설 점검 보고]\n시간: {get_korea_timestamp()}\n점검자: {staff}\n유형: {task}\n특이사항: {memo}"
                send_kakao_message(msg)

# === [TAB 3] 👑 관리자 대시보드 (로그인 시에만 보임) ===
if tab3 and sheet:
    with tab3:
        st.header("👑 MAP ADMIN DASHBOARD")
        st.info("모든 데이터는 실시간으로 구글 시트에서 불러옵니다.")
        
        if st.button("🔄 데이터 새로고침"):
            st.rerun()
            
        # 데이터 불러오기
        try:
            data = sheet.get_all_values()
            if len(data) > 1:
                df = pd.DataFrame(data[1:], columns=["Timestamp", "Type", "Detail1", "Detail2", "Detail3", "Detail4", "RawData"])
                
                # 1. 통계 요약 (Metrics)
                st.markdown("### 📊 실시간 현황")
                m1, m2, m3, m4 = st.columns(4)
                
                total_logs = len(df)
                pt_logs = len(df[df['Type'].str.contains("PT", na=False)])
                fac_logs = len(df[df['Type'].str.contains("FACILITY", na=False)])
                today_logs = len(df[df['Timestamp'].str.contains(get_korea_timestamp()[:10], na=False)])
                
                m1.metric("총 누적 데이터", f"{total_logs}건")
                m2.metric("오늘 생성된 로그", f"{today_logs}건", "+New")
                m3.metric("PT 분석 리포트", f"{pt_logs}건")
                m4.metric("시설 점검 리포트", f"{fac_logs}건")
                
                st.divider()
                
                # 2. 데이터 필터링 및 조회
                st.markdown("### 📋 전체 로그 조회")
                filter_type = st.selectbox("로그 유형 필터", ["전체 보기", "PT 리포트만 보기", "시설 점검만 보기"])
                
                view_df = df
                if filter_type == "PT 리포트만 보기":
                    view_df = df[df['Type'].str.contains("PT", na=False)]
                elif filter_type == "시설 점검만 보기":
                    view_df = df[df['Type'].str.contains("FACILITY", na=False)]
                
                # 최신순 정렬
                view_df = view_df.sort_values(by="Timestamp", ascending=False)
                st.dataframe(view_df, use_container_width=True)
                
                # 3. 데이터 다운로드
                csv = view_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 엑셀(CSV)로 다운로드", csv, "map_log_data.csv", "text/csv")
                
            else:
                st.warning("데이터가 아직 없습니다.")
        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
