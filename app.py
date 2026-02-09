import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai

# -----------------------------------------------------------------------------
# 1. 시스템 설정 & 스타일
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .main {background-color: #0E1117;}
    .status-badge {padding: 5px 10px; border-radius: 5px; font-weight: bold; color: white;}
    .status-ok {background-color: #1f7a1f;}
    .status-err {background-color: #cf1322;}
    .result-box {padding: 15px; border-radius: 10px; margin: 10px 0; font-weight: bold; color: white;}
    .res-stop {background: #cf1322;}
    .res-mod {background: #d48806;}
    .res-go {background: #1f7a1f;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 핵심 함수 (시간, DB 연결)
# -----------------------------------------------------------------------------
def get_korea_timestamp():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

def connect_db():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secrets에 gcp_service_account가 없습니다."

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]),
            scope
        )
        gc = gspread.authorize(creds)

        doc = gc.open("MAP_DATABASE")
        sheet = doc.sheet1  # 필요하면 worksheet("LOG")로 변경 권장
        return sheet, f"연결 성공 (탭: {sheet.title})"

    except Exception as e:
        return None, f"연결 실패: {e}"

def safe_append_row(sheet, row):
    """쓰기 실패를 화면에 확실히 보여주기 위한 래퍼"""
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e:
        return False, str(e)

# -----------------------------------------------------------------------------
# 3. 사이드바 (진단)
# -----------------------------------------------------------------------------
st.sidebar.title("관리자 진단 도구")

sheet, db_msg = connect_db()
if sheet:
    st.sidebar.success(db_msg)
else:
    st.sidebar.error(db_msg)

if st.sidebar.button("DB 쓰기 테스트 (Debug)"):
    if sheet:
        ok, err = safe_append_row(sheet, [
            get_korea_timestamp(),
            "DEBUG_TEST",
            "시스템 점검",
            "쓰기 권한 확인",
            "OK",
            "관리자"
        ])
        if ok:
            st.sidebar.success("쓰기 성공 (권한 정상)")
        else:
            st.sidebar.error(f"쓰기 실패: {err}")
    else:
        st.sidebar.error("DB 연결부터 확인하세요.")

# OpenAI
if "OPENAI_API_KEY" in st.secrets and st.secrets["OPENAI_API_KEY"]:
    ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    st.sidebar.success("AI 엔진 Ready")
else:
    ai_client = None
    st.sidebar.warning("OpenAI 키 없음")

# -----------------------------------------------------------------------------
# 4. 메인
# -----------------------------------------------------------------------------
st.title("MAP INTEGRATED SYSTEM")
st.write(f"Time (KST): {get_korea_timestamp()}")

tab1, tab2 = st.tabs(["PT 안전 분류", "시설 관리 로그"])

# -----------------------------------------------------------------------------
# TAB 1: PT 안전 분류
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("PT 수업 전 행정적 안전 분류")
    st.caption("본 시스템은 의료 진단이 아니며, 보수적 안전 분류를 위한 기록 도구입니다.")

    with st.form("pt_form"):
        c1, c2 = st.columns(2)
        with c1:
            member = st.text_input("회원 정보", placeholder="예: 50대 남성, 허리디스크 과거력")
            symptom = st.text_input("현재 컨디션/증상", placeholder="예: 오늘 허리 뻐근함")
        with c2:
            exercise = st.text_input("수행 예정 운동", placeholder="예: 데드리프트")

        btn = st.form_submit_button("리스크 분석")

    if btn:
        if not ai_client:
            st.error("AI 엔진이 연결되지 않았습니다(OPENAI_API_KEY 확인).")
        elif not sheet:
            st.error("DB가 연결되지 않았습니다(gcp_service_account / 시트 공유 확인).")
        elif not (member and symptom and exercise):
            st.warning("입력 3개 항목을 모두 채워주세요.")
        else:
            with st.spinner("MAP 기준으로 분류 중..."):
                prompt = f"""
Role: Safety Administration Officer for a Gym (NOT a Doctor).
Tone: Dry, administrative, conservative.
Task: Categorize risk for the following session.

Input:
- Member: {member}
- Symptom/Condition: {symptom}
- Planned Exercise: {exercise}

Rules:
- STOP: direct conflict with pain area / high aggravation likelihood
- MODIFICATION: partial conflict / reduce load, change pattern
- GO: no apparent conflict

Output requirements:
1) First line must be exactly one of: STOP / MODIFICATION / GO
2) Second line: short dry reason (Korean, 1 sentence)
No medical advice. No motivation. No long explanations.
"""
                try:
                    response = ai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                    )
                    res = (response.choices[0].message.content or "").strip()

                    first = (res.splitlines()[0].strip().upper() if res else "")
                    if first not in ["STOP", "MODIFICATION", "GO"]:
                        # 안전장치: 모델이 형식 어기면 MODIFICATION으로 강등
                        first = "MODIFICATION"

                    if first == "STOP":
                        st.markdown(f"<div class='result-box res-stop'>{res}</div>", unsafe_allow_html=True)
                    elif first == "MODIFICATION":
                        st.markdown(f"<div class='result-box res-mod'>{res}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='result-box res-go'>{res}</div>", unsafe_allow_html=True)

                    # 저장: decision + 원문(res) 일부를 같이 보관
                    ok, err = safe_append_row(sheet, [
                        get_korea_timestamp(),
                        "PT_SAFETY",
                        member,
                        symptom,
                        exercise,
                        first,
                        res[:300]  # 시트 칼럼 여유 있으면 늘려도 됨
                    ])
                    if ok:
                        st.success("PT 로그 저장 완료")
                    else:
                        st.error(f"PT 로그 저장 실패: {err}")

                except Exception as e:
                    st.error(f"AI 호출 오류: {e}")

# -----------------------------------------------------------------------------
# TAB 2: 시설 관리 로그
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("시설 안전 관리 로그")
    st.caption("사고 발생 시 관리 의무 이행을 입증하기 위한 건조 기록입니다.")

    with st.form("facility_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            task = st.selectbox("작업 유형", ["정기 순찰", "안전 교육(OT)", "기구 정비"])
        with c2:
            location = st.selectbox("구역", ["유산소존", "머신존", "프리웨이트존", "탈의실/샤워실"])
        with c3:
            staff = st.text_input("점검자 실명", placeholder="예: 홍길동")

        action = st.text_input("조치/특이사항", placeholder="예: 이상 없음 / 바닥 물기 제거 / 3번 머신 사용중지 안내")
        save = st.form_submit_button("로그 저장")

    if save:
        if not sheet:
            st.error("DB가 연결되지 않았습니다.")
        elif not staff:
            st.warning("점검자 실명을 입력해주세요.")
        else:
            ok, err = safe_append_row(sheet, [
                get_korea_timestamp(),
                "FACILITY_LOG",
                task,
                location,
                action,
                staff
            ])
            if ok:
                st.success("시설 로그 저장 완료")
            else:
                st.error(f"시설 로그 저장 실패: {err}")
