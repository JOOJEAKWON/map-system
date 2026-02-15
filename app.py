import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import pandas as pd
import re

# -----------------------------------------------------------------------------
# 1. 시스템 설정 & 스타일 (Clean & Luxury White)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    /* 전체 배경: 깨끗한 화이트 */
    .main {background-color: #FFFFFF; color: #333;}
    
    /* 입력 폼: 부드러운 그림자의 카드 스타일 */
    .stForm {
        background-color: #F8F9FA; 
        padding: 25px; 
        border-radius: 15px; 
        border: 1px solid #E9ECEF;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }
    
    /* 결과 박스: 가독성 최적화 */
    .result-box {
        padding: 25px; 
        border-radius: 12px; 
        margin: 20px 0; 
        border: 1px solid #ddd; 
        font-size: 1.1em;
        line-height: 1.7;
    }
    .result-box h1, .result-box h2, .result-box strong {color: #111 !important; font-weight: 800;}
    
    /* 상태별 컬러 테마 (파스텔 + 진한 포인트) */
    .res-stop {background-color: #FFF5F5; border-left: 8px solid #FF4B4B; color: #8B0000 !important;} 
    .res-mod {background-color: #FFF8E1; border-left: 8px solid #FFA500; color: #8B4500 !important;}
    .res-go {background-color: #F1F8E9; border-left: 8px solid #00C853; color: #1B5E20 !important;}
    
    /* 카카오톡 미리보기 영역 */
    .kakao-preview {
        background-color: #FEE500; 
        color: #3b1e1e; 
        padding: 15px; 
        border-radius: 10px; 
        font-size: 0.95em; 
        margin-top: 10px;
        border: 1px dashed #cfba00;
    }
    
    /* 관리자 대시보드 카드 */
    .metric-card {
        background-color: #fff; border: 1px solid #eee; padding: 20px; 
        border-radius: 12px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
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
        res = requests.post(url, headers=headers, data=data)
        return (True, "성공") if res.status_code == 200 else (False, f"실패({res.status_code})")
    except Exception as e: return False, str(e)

def safe_append_row(sheet, row):
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e: return False, str(e)

# -----------------------------------------------------------------------------
# 3. 사이드바 (로그인 & 상태)
# -----------------------------------------------------------------------------
st.sidebar.title("🔐 관리자 접속")

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    password = st.sidebar.text_input("비밀번호", type="password")
    if st.sidebar.button("로그인"):
        if password == "1234": # 비밀번호 변경 가능
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.sidebar.error("비밀번호가 틀렸습니다.")
else:
    st.sidebar.success("👑 관리자 모드 ON")
    if st.sidebar.button("로그아웃"):
        st.session_state.admin_logged_in = False
        st.rerun()

sheet, db_msg = connect_db()
if not sheet: st.error(f"DB 오류: {db_msg}")

if "OPENAI_API_KEY" in st.secrets:
    ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    ai_client = None

# -----------------------------------------------------------------------------
# 4. 프롬프트 (KOREAN PRO VER.) - 전문성(한글) + 감성(카톡)
# -----------------------------------------------------------------------------
MAP_CORE_PROMPT = """
# MASTER SYSTEM: MAP_INTEGRATED_CORE_v2026 (KOREAN_PRO)
# PRIORITY: Legal Safety > Operational Structure > Member Care

**[SYSTEM ROLE]**
1. **Internal Brain (Analysis):** Professional Safety Officer.
2. **External Voice (KakaoTalk):** High-end Concierge.

**[ABSOLUTE RULES (LEGAL SAFETY)]**
1. **NO MEDICAL PRACTICE:** Do NOT use words like '진단', '치료', '처방', '완치'.
2. **ADMINISTRATIVE TONE:** Use words like '분류', '관리', '가이드', '리스크 확인'.
3. **LANGUAGE:** Output ALL SECTIONS in **Professional Korean**.

**[OUTPUT FORMATS]**
You MUST output the response in the following structured sections using Markdown:

### 1. 📋 FSL 현장 리포트 (Internal Admin)
---
**[MAP ANALYSIS : {Timestamp}]**
**Target:** {Client_Tag}
**Plan:** {Exercise_Summary}

**1. 판정:** [GO] or [MODIFICATION] or [STOP]
(Strict biomechanical decision)

**2. 리스크 요인:**
- (Explain in professional Korean. e.g., "요추 4-5번 디스크 병력으로 인해 수직 압축 부하 발생 시 통증 악화 우려.")

**3. 액션 프로토콜:**
- ⛔ **제한:** (e.g., "중량 부하 제한", "가동범위 축소")
- ✅ **대체:** (e.g., "척추 중립이 확보되는 힙 힌지 패턴으로 변경")
- ⚠️ **큐잉:** (e.g., "복압 유지 및 통증 발생 시 즉시 중단 신호")
---

### 2. 🔬 MAP 상세 분석 로그
---
**Red Flag Check:** (Pass or Fail / Reason in Korean)
**Mechanism Check:** (Biomechanics logic in Korean)
**Sanitization:** (Masked)
---

### 3. 💬 카카오톡 전송 템플릿 (Client Facing)
---
(Warm, polite, caring tone. Emojis allowed.)

안녕하세요, **{Client_Tag}**님! 👋
**킹스짐(King's Gym) 안전관리팀**입니다.

오늘 컨디션을 확인해보니 **{Exercise_Summary}** 진행 시 조금 더 세심한 주의가 필요할 것 같아요. 🧐

회원님의 소중한 몸을 보호하기 위해, 오늘은 무리한 진행보다는
👉 **(Write a warm suggestion based on the protocol. e.g., "허리 부담을 줄이는 안전한 자세로", "컨디션 회복을 위한 맞춤 운동으로")**
방향을 잡아드리고자 합니다.

작은 불편함도 놓치지 않고, 가장 안전하고 효율적인 길로 안내하겠습니다.
현장에서 트레이너 선생님의 가이드를 잘 따라주세요! 💪

(본 알림은 회원님의 안전을 위한 행정적 가이드입니다.)
---
"""

# -----------------------------------------------------------------------------
# 5. 메인 UI (Dashboard Layout)
# -----------------------------------------------------------------------------
st.title("🛡️ MAP INTEGRATED SYSTEM")
st.write(f"🕒 Time (KST): **{get_korea_timestamp()}**")

# 탭 구성
if st.session_state.admin_logged_in:
    tab1, tab2, tab3 = st.tabs(["🧬 PT 안전 분류", "🏢 시설 관리 로그", "👑 관리자 대시보드"])
else:
    tab1, tab2 = st.tabs(["🧬 PT 안전 분류", "🏢 시설 관리 로그"])
    tab3 = None

# === [TAB 1] PT 안전 분류 (Smart Form) ===
with tab1:
    with st.container():
        st.markdown("### 📋 PT 세션 안전 점검")
        with st.form("pt_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**👤 회원 정보**")
                member = st.text_input("회원 특이사항", placeholder="예: 50대 남성, 허리디스크")
                
                st.markdown("**🩺 컨디션 체크 (빠른 선택)**")
                body_part = st.selectbox("주요 통증/불편 부위", 
                                       ["없음 (양호)", "허리 (Lumbar)", "무릎 (Knee)", "어깨 (Shoulder)", "목 (Neck)", "손목/발목", "직접 입력"])
                
                detail_symptom = ""
                if body_part == "직접 입력": detail_symptom = st.text_input("증상 상세 입력")
                elif body_part != "없음 (양호)": detail_symptom = body_part + " 통증/불편감"
                else: detail_symptom = "특이사항 없음"

            with col2:
                st.markdown("**🏋️ 운동 계획**")
                exercise = st.text_input("수행 예정 운동", placeholder="예: 데드리프트, 스쿼트")
                
                st.markdown("**📨 옵션**")
                send_k = st.checkbox("✅ 분석 결과를 카카오톡으로 전송", value=True)
                
            st.divider()
            btn = st.form_submit_button("🚀 CORE 엔진 분석 실행", use_container_width=True)

    if btn:
        if ai_client and sheet:
            final_symptom = detail_symptom
            
            with st.status("🧠 Singularity 엔진 가동 중...", expanded=True) as status:
                try:
                    status.write("🔍 1단계: 회원 데이터 및 컨디션 파싱...")
                    # 프롬프트 조립 (f-string 에러 방지용 format 사용)
                    final_prompt = MAP_CORE_PROMPT.format(
                        Timestamp=get_korea_timestamp(),
                        Client_Tag=member,
                        Exercise_Summary=exercise
                    )
                    final_prompt += f"\n\n[INPUT DATA]\nMember: {member}\nSymptom: {final_symptom}\nExercise: {exercise}\n\nAnalyze now."

                    status.write("⚖️ 2단계: 생체역학적 리스크 & 감성 메시지 생성 중...")
                    response = ai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": final_prompt}],
                        temperature=0.3 # 약간의 창의성 허용 (감성 메시지용)
                    )
                    full_res = response.choices[0].message.content
                    
                    status.write("💾 3단계: 보안 데이터베이스 기록 중...")
                    kakao_msg = extract_kakao_message(full_res)
                    safe_append_row(sheet, [get_korea_timestamp(), "PT_CORE_ANALYSIS", member, final_symptom, exercise, "DONE", full_res[:4000]])
                    
                    status.update(label="✅ 분석 완료! 아래 리포트를 확인하세요.", state="complete", expanded=False)
                    
                    # 결과 출력
                    if "[STOP]" in full_res: css = "res-stop"
                    elif "[MODIFICATION]" in full_res: css = "res-mod"
                    else: css = "res-go"
                    
                    st.markdown(f"<div class='result-box {css}'>{full_res}</div>", unsafe_allow_html=True)

                    if send_k:
                        k_ok, k_err = send_kakao_message(kakao_msg)
                        if k_ok: st.success("💬 카톡 전송 완료!")
                        else: st.warning(f"카톡 전송 실패: {k_err}")

                except Exception as e: 
                    status.update(label="❌ 오류 발생", state="error")
                    st.error(f"시스템 에러: {e}")

# === [TAB 2] 시설 관리 (Speedy Log) ===
with tab2:
    with st.container():
        st.markdown("### 🛠️ 시설 안전 점검 로그")
        with st.form("fac_form"):
            col1, col2 = st.columns(2)
            with col1:
                task = st.radio("작업 유형", ["시설 순찰 (Patrol)", "기구 정비 (Fix)", "청소/환경 (Clean)", "기타 조치"], horizontal=True)
                place = st.radio("점검 구역", ["웨이트존", "유산소존", "탈의실/샤워장", "프리웨이트/GX"], horizontal=True)
            with col2:
                memo = st.text_input("특이사항 / 조치내용", "이상 없음 (Clear)")
                staff = st.text_input("점검자 서명")
                send_k_fac = st.checkbox("지점장님께 카톡 보고", value=True)
            
            st.divider()
            save = st.form_submit_button("📝 점검 기록 저장", use_container_width=True)

    if save:
        if sheet and staff:
            ok, err = safe_append_row(sheet, [get_korea_timestamp(), "FACILITY", task, place, memo, staff])
            if ok:
                st.success(f"✅ [{task}] 저장 완료")
                if send_k_fac:
                    msg = f"[시설 점검 보고]\n시간: {get_korea_timestamp()}\n점검자: {staff}\n유형: {task}\n특이사항: {memo}"
                    send_kakao_message(msg)
            else: st.error(f"저장 실패: {err}")
        elif not staff:
            st.warning("⚠️ 점검자 이름을 입력해주세요.")

# === [TAB 3] 👑 관리자 대시보드 (Admin Only) ===
if tab3 and sheet:
    with tab3:
        st.header("👑 MAP ADMIN DASHBOARD")
        st.caption("실시간 데이터 분석 및 로그 조회")
        
        if st.button("🔄 데이터 새로고침"): st.rerun()
            
        try:
            data = sheet.get_all_values()
            if len(data) > 1:
                df = pd.DataFrame(data[1:], columns=["Timestamp", "Type", "Detail1", "Detail2", "Detail3", "Detail4", "RawData"])
                
                # 1. 통계 지표
                st.markdown("#### 📊 실시간 현황")
                m1, m2, m3, m4 = st.columns(4)
                
                total = len(df)
                today_cnt = len(df[df['Timestamp'].str.contains(get_korea_timestamp()[:10], na=False)])
                pt_cnt = len(df[df['Type'].str.contains("PT", na=False)])
                fac_cnt = len(df[df['Type'].str.contains("FACILITY", na=False)])
                
                m1.metric("총 누적 데이터", f"{total}건")
                m2.metric("오늘 생성된 로그", f"{today_cnt}건", "+New")
                m3.metric("PT 분석 리포트", f"{pt_cnt}건")
                m4.metric("시설 점검 리포트", f"{fac_cnt}건")
                
                st.divider()
                
                # 2. 로그 뷰어
                st.markdown("#### 📋 전체 로그 데이터")
                filter_opt = st.selectbox("필터링", ["전체 보기", "PT 리포트만", "시설 점검만"])
                
                view_df = df
                if filter_opt == "PT 리포트만": view_df = df[df['Type'].str.contains("PT", na=False)]
                elif filter_opt == "시설 점검만": view_df = df[df['Type'].str.contains("FACILITY", na=False)]
                
                view_df = view_df.sort_values(by="Timestamp", ascending=False)
                st.dataframe(view_df, use_container_width=True)
                
                # 3. 다운로드
                csv = view_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 엑셀(CSV) 다운로드", csv, "map_logs.csv", "text/csv")
            else:
                st.info("데이터가 없습니다.")
        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
