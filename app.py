import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import json
import re
import time

# =============================================================================
# 0. 기본 설정
# =============================================================================
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

# =============================================================================
# 1. 스타일 (가독성/사용감 최적화)
# =============================================================================
st.markdown(
    """
<style>
/* 전체 배경 */
.main { background-color: #FFFFFF; color: #111111; }

/* 상단 상태바 */
.topbar {
    display:flex; justify-content: space-between; align-items:center;
    padding: 12px 14px; border: 1px solid #E6E6E6; border-radius: 12px;
    background: #FAFAFA; margin-bottom: 14px;
}
.topbar .left { font-size: 14px; color:#222; }
.topbar .right { display:flex; gap:10px; align-items:center; }
.badge {
    padding: 6px 10px; border-radius: 999px; font-size: 12px;
    border: 1px solid #E6E6E6; background:#FFFFFF; color:#222;
}
.badge-ok { border-color:#BFE8C7; background:#EAF7ED; color:#0B3D18; }
.badge-err { border-color:#F1B5B5; background:#FCECEC; color:#5A0B0B; }
.badge-warn { border-color:#F0D7A7; background:#FFF6E5; color:#5B3A00; }

/* 섹션 카드 */
.card {
    border: 1px solid #E6E6E6; border-radius: 14px;
    background: #FFFFFF; padding: 16px; margin-bottom: 14px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.card-title { font-size: 16px; font-weight: 800; margin-bottom: 10px; color:#111; }
.card-sub { font-size: 13px; color:#444; margin-top: -6px; margin-bottom: 12px; }

/* 판정 배너 */
.decision-banner {
    padding: 18px 16px; border-radius: 14px; border: 1px solid #E6E6E6;
    display:flex; justify-content: space-between; align-items:center;
    margin-bottom: 12px;
}
.decision-left { display:flex; flex-direction: column; gap:4px; }
.decision-tag { font-size: 12px; font-weight: 700; opacity: 0.9; }
.decision-main { font-size: 22px; font-weight: 900; letter-spacing: 0.5px; }
.decision-desc { font-size: 13px; color:#222; opacity: 0.95; }
.decision-meta { font-size: 12px; color:#333; opacity: 0.8; text-align:right; }

.dec-go { background:#EAF7ED; border-color:#BFE8C7; color:#0B3D18; }
.dec-mod { background:#FFF6E5; border-color:#F0D7A7; color:#5B3A00; }
.dec-stop { background:#FCECEC; border-color:#F1B5B5; color:#5A0B0B; }

/* 보고서 본문 */
.report {
    border: 1px solid #EDEDED; border-radius: 14px;
    background: #FCFCFC; padding: 14px;
    line-height: 1.65; font-size: 15px; color:#111;
}
.report h1, .report h2, .report h3 { color:#111 !important; font-weight: 900; }
.report strong { color:#111 !important; font-weight: 900; }

/* 카카오 박스 */
.kakao {
    border: 1px solid #F3E57A; border-radius: 14px;
    background: #FFF7CC; padding: 14px; line-height: 1.6;
    color:#2E1C00;
}

/* 작은 도움말 */
.hint { font-size: 12px; color:#555; margin-top: 6px; }
hr { border: none; border-top: 1px solid #EFEFEF; margin: 12px 0; }
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# 2. 유틸
# =============================================================================
def get_korea_timestamp() -> str:
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

def connect_db():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secrets에 gcp_service_account가 없습니다."
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        gc = gspread.authorize(creds)
        doc = gc.open("MAP_DATABASE")
        sheet = doc.sheet1
        return sheet, f"연결 성공 (시트 탭: {sheet.title})"
    except Exception as e:
        return None, f"연결 실패: {str(e)}"

def safe_append_row(sheet, row, retries=3, sleep_sec=0.8):
    """
    구글 시트 저장 신뢰성 강화:
    - 네트워크/일시 오류 재시도
    - 실패 시 원인 반환
    """
    last_err = None
    for _ in range(retries):
        try:
            sheet.append_row(row, value_input_option="USER_ENTERED")
            return True, None
        except Exception as e:
            last_err = str(e)
            time.sleep(sleep_sec)
    return False, last_err

def send_kakao_message(text: str):
    """
    카카오 나에게 보내기(메모) API.
    주의: template_object는 JSON 문자열이어야 합니다.
    """
    try:
        if "KAKAO_TOKEN" not in st.secrets:
            return False, "KAKAO_TOKEN이 Secrets에 없습니다."
        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        headers = {"Authorization": "Bearer " + st.secrets["KAKAO_TOKEN"]}
        payload = {
            "object_type": "text",
            "text": text,
            "link": {"web_url": "https://streamlit.io", "mobile_web_url": "https://streamlit.io"},
        }
        data = {"template_object": json.dumps(payload, ensure_ascii=False)}
        res = requests.post(url, headers=headers, data=data, timeout=10)
        if res.status_code == 200:
            return True, None
        return False, f"HTTP {res.status_code}: {res.text[:200]}"
    except Exception as e:
        return False, str(e)

def extract_decision(text: str) -> str:
    """
    최상위 판정 단일화(가장 중요):
    모델 출력에서 STOP/MODIFICATION/GO를 단 하나로 추출합니다.
    우선순위: STOP > MODIFICATION > GO (충돌 시 보수적으로)
    """
    t = (text or "").upper()
    has_stop = ("[STOP]" in t) or re.search(r"\bSTOP\b", t)
    has_mod = ("[MODIFICATION]" in t) or re.search(r"\bMODIFICATION\b", t) or re.search(r"\bCAUTION\b", t)
    has_go = ("[GO]" in t) or re.search(r"\bGO\b", t)
    if has_stop:
        return "STOP"
    if has_mod:
        return "MODIFICATION"
    if has_go:
        return "GO"
    return "MODIFICATION"

def split_sections(full_text: str):
    """
    보고서/내부로그/카카오 섹션 분리.
    실패해도 전체 텍스트를 보고서로 보여줍니다.
    """
    text = full_text or ""
    kakao = ""
    internal = ""
    report = text

    # 카카오 섹션
    m_k = re.search(r"###\s*3\.\s*.*?카카오톡.*?\n---\n(.*?)(\n---\s*$|\Z)", text, re.DOTALL)
    if m_k:
        kakao = m_k.group(1).strip()

    # 내부 로그 섹션
    m_i = re.search(r"###\s*2\.\s*.*?상세 분석.*?\n---\n(.*?)(\n---\s*###\s*3\.|\Z)", text, re.DOTALL)
    if m_i:
        internal = m_i.group(1).strip()

    # 보고서 섹션(1번)
    m_r = re.search(r"###\s*1\.\s*.*?\n---\n(.*?)(\n---\s*###\s*2\.|\Z)", text, re.DOTALL)
    if m_r:
        report = m_r.group(1).strip()

    return report, internal, kakao

# =============================================================================
# 3. 프롬프트 (고정: 일관성 확보)
# =============================================================================
MAP_CORE_PROMPT = """
# MASTER SYSTEM: MAP_INTEGRATED_CORE_v2026 (SMART-LITE)
# ROLE: Non-medical Safety Administration System for Gyms

[PRIORITY ORDER]
1) Legal defensibility (dry, factual, administrative)
2) Operational usability (fast, consistent)
3) Member-facing care (polite, minimal)

[CORE RULES]
- This is NOT a medical diagnosis.
- Be conservative when there is a plausible load conflict.
- Always choose exactly ONE decision: STOP / MODIFICATION / GO.
- Avoid long explanations. No emotional language.

[OUTPUT FORMAT]
You MUST output the response in the following structured sections using Markdown, exactly:

### 1. FSL Administrative Report
---
[MAP ANALYSIS : {Timestamp}]
Target: {Client_Tag}
Plan: {Exercise_Summary}

Decision: [STOP] or [MODIFICATION] or [GO]
Reason: (1 short administrative sentence, Korean)
Restriction: (1 short line)
Alternative: (1 short line)
Cue: (1 short line)
---

### 2. Internal Check Matrix
---
RedFlag: PASS/FAIL
LoadConflict: DIRECT/INDIRECT/NONE
Sanitization: APPLIED
---

### 3. Kakao Message Template
---
안녕하세요, {Client_Tag}님.
MAP 트레이닝 센터입니다.

오늘 컨디션을 고려하여 안전을 우선으로 안내드립니다.
오늘 진행 포인트: (1 short safe sentence)

감사합니다.
---
"""

# =============================================================================
# 4. 연결 상태 로드
# =============================================================================
sheet, db_msg = connect_db()

ai_client = None
ai_msg = "OpenAI 키가 없습니다."
try:
    if "OPENAI_API_KEY" in st.secrets and str(st.secrets["OPENAI_API_KEY"]).strip():
        ai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        ai_msg = "AI 연결됨"
except Exception as e:
    ai_client = None
    ai_msg = f"AI 연결 실패: {str(e)}"

# =============================================================================
# 5. 상단 UI
# =============================================================================
left = f"System Time (KST): {get_korea_timestamp()}"
if sheet:
    db_badge = f"<span class='badge badge-ok'>DB: ONLINE</span>"
else:
    db_badge = f"<span class='badge badge-err'>DB: OFFLINE</span>"

if ai_client:
    ai_badge = f"<span class='badge badge-ok'>AI: READY</span>"
else:
    ai_badge = f"<span class='badge badge-err'>AI: NOT READY</span>"

st.markdown(
    f"""
<div class="topbar">
  <div class="left">{left}</div>
  <div class="right">
    {db_badge}
    {ai_badge}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# 6. 메인 탭
# =============================================================================
tab1, tab2 = st.tabs(["PT 사전 안전 분류", "시설 안전 로그"])

# -----------------------------------------------------------------------------
# TAB 1: PT
# -----------------------------------------------------------------------------
with tab1:
    st.markdown("<div class='card'><div class='card-title'>PT 세션 사전 안전 분류</div>"
                "<div class='card-sub'>본 기능은 의료 진단이 아닌, 안전 및 법적 방어를 위한 행정 분류 기록입니다.</div></div>",
                unsafe_allow_html=True)

    with st.form("pt_form"):
        c1, c2 = st.columns([1, 1])

        with c1:
            st.markdown("<div class='card'><div class='card-title'>입력</div>", unsafe_allow_html=True)
            member = st.text_input("회원 식별(이름 또는 태그)", placeholder="예: 김OO / 50대 남성 / 디스크 과거력")
            symptom_pick = st.selectbox(
                "주요 불편 부위(빠른 선택)",
                ["특이사항 없음", "허리", "무릎", "어깨", "목", "손목/팔꿈치", "발목/고관절", "직접 입력"],
                index=0
            )
            symptom_detail = ""
            if symptom_pick == "직접 입력":
                symptom_detail = st.text_input("증상 상세", placeholder="예: 오른쪽 무릎 내측 통증, 계단 시 악화")
            elif symptom_pick == "특이사항 없음":
                symptom_detail = "특이사항 없음"
            else:
                symptom_detail = f"{symptom_pick} 불편감"

            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='card'><div class='card-title'>운동 계획 및 옵션</div>", unsafe_allow_html=True)
            exercise = st.text_input("수행 예정 운동", placeholder="예: 데드리프트 / 스쿼트 / 벤치프레스")
            send_k = st.checkbox("결과를 카카오톡으로 전송", value=False)
            save_db = st.checkbox("결과를 DB에 저장", value=True)
            st.markdown("<div class='hint'>저장 실패 시에는 우측 상단 DB 상태와 관리자 진단(사이드바)을 확인하십시오.</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        submit = st.form_submit_button("분석 실행", use_container_width=True)

    # 사이드바 진단
    st.sidebar.markdown("관리자 진단")
    st.sidebar.write(f"DB: {db_msg}")
    st.sidebar.write(f"AI: {ai_msg}")

    if st.sidebar.button("DB 쓰기 테스트"):
        if not sheet:
            st.sidebar.error("DB가 OFFLINE입니다. Secrets/공유 권한/시트 이름을 확인하십시오.")
        else:
            ok, err = safe_append_row(sheet, [get_korea_timestamp(), "DEBUG_TEST", "WRITE_CHECK", "OK"])
            if ok:
                st.sidebar.success("쓰기 성공")
            else:
                st.sidebar.error(f"쓰기 실패: {err}")

    if submit:
        # 입력 검증
        if not member.strip():
            st.error("회원 식별을 입력하십시오.")
            st.stop()
        if not exercise.strip():
            st.error("수행 예정 운동을 입력하십시오.")
            st.stop()
        if not ai_client:
            st.error("AI가 준비되지 않았습니다. Secrets의 OPENAI_API_KEY를 확인하십시오.")
            st.stop()

        # 프롬프트 구성
        prompt = MAP_CORE_PROMPT.format(
            Timestamp=get_korea_timestamp(),
            Client_Tag=member.strip(),
            Exercise_Summary=exercise.strip(),
        )
        prompt += f"\n\n[INPUT]\nMember: {member.strip()}\nSymptom: {symptom_detail.strip()}\nExercise: {exercise.strip()}\n"

        with st.status("분석 및 기록 처리 중", expanded=True) as status:
            # 1) AI 호출
            status.write("AI 분석 실행")
            try:
                res = ai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": prompt}],
                    temperature=0.2
                )
                full_text = res.choices[0].message.content or ""
            except Exception as e:
                status.update(label="AI 호출 실패", state="error", expanded=True)
                st.error(f"AI 호출 오류: {str(e)}")
                st.stop()

            # 2) 판정 단일화(최상단 배너와 본문 충돌 방지)
            decision = extract_decision(full_text)

            # 3) 섹션 분리
            report, internal, kakao = split_sections(full_text)

            # 4) 상단 판정 배너 (항상 decision 기준)
            if decision == "STOP":
                banner_cls = "dec-stop"
                desc = "고위험으로 분류됩니다. 즉시 중단 또는 대체가 필요합니다."
            elif decision == "MODIFICATION":
                banner_cls = "dec-mod"
                desc = "주의가 필요합니다. 강도 조정 또는 대체가 필요합니다."
            else:
                banner_cls = "dec-go"
                desc = "특이 충돌이 낮습니다. 안전 수칙 준수 하에 진행 가능합니다."

            st.markdown(
                f"""
<div class="decision-banner {banner_cls}">
  <div class="decision-left">
    <div class="decision-tag">Decision</div>
    <div class="decision-main">{decision}</div>
    <div class="decision-desc">{desc}</div>
  </div>
  <div class="decision-meta">
    <div>Target: {member.strip()}</div>
    <div>Plan: {exercise.strip()}</div>
    <div>Time: {get_korea_timestamp()}</div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

            # 5) 보고서 본문 (가독성 정리)
            status.write("보고서 표시")
            st.markdown("<div class='card'><div class='card-title'>FSL Report</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='report'>{report}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # 6) 내부 로그 / 카카오 (접기)
            with st.expander("Internal Check Matrix", expanded=False):
                if internal.strip():
                    st.markdown(f"<div class='report'>{internal}</div>", unsafe_allow_html=True)
                else:
                    st.write("내부 로그가 포함되지 않았습니다.")

            with st.expander("Kakao Message Template", expanded=True):
                if kakao.strip():
                    st.markdown(f"<div class='kakao'>{kakao}</div>", unsafe_allow_html=True)
                else:
                    st.write("카카오 템플릿이 포함되지 않았습니다.")

            # 7) DB 저장 (핵심: 저장 성공/실패를 확실히 표시)
            if save_db:
                status.write("DB 저장 시도")
                if not sheet:
                    status.update(label="DB 저장 실패", state="error", expanded=True)
                    st.error("DB가 OFFLINE입니다. 시트 공유 권한 및 Secrets를 확인하십시오.")
                else:
                    row = [
                        get_korea_timestamp(),
                        "PT_CORE_ANALYSIS",
                        member.strip(),
                        symptom_detail.strip(),
                        exercise.strip(),
                        decision,
                        (full_text[:4000] if full_text else "")
                    ]
                    ok, err = safe_append_row(sheet, row)
                    if ok:
                        status.write("DB 저장 성공")
                    else:
                        status.update(label="DB 저장 실패", state="error", expanded=True)
                        st.error(f"DB 저장 실패: {err}")

            # 8) 카카오 전송
            if send_k:
                status.write("카카오 전송 시도")
                if not kakao.strip():
                    st.warning("카카오 템플릿이 비어 있어 전송을 생략합니다.")
                else:
                    k_ok, k_err = send_kakao_message(kakao.strip())
                    if k_ok:
                        status.write("카카오 전송 성공")
                    else:
                        st.warning(f"카카오 전송 실패: {k_err}")

            status.update(label="완료", state="complete", expanded=False)

# -----------------------------------------------------------------------------
# TAB 2: 시설 로그
# -----------------------------------------------------------------------------
with tab2:
    st.markdown("<div class='card'><div class='card-title'>시설 안전 로그</div>"
                "<div class='card-sub'>건조한 사실 기록만 남기며, 불필요한 과장 표현을 사용하지 않습니다.</div></div>",
                unsafe_allow_html=True)

    with st.form("facility_form"):
        c1, c2 = st.columns([1, 1])

        with c1:
            st.markdown("<div class='card'><div class='card-title'>작업 선택</div>", unsafe_allow_html=True)
            task = st.radio("작업 유형", ["시설 순찰", "기구 정비", "청소/환경", "기타 조치"], horizontal=True)
            place = st.radio("점검 구역", ["웨이트존", "유산소존", "탈의실/샤워장", "프리웨이트/GX"], horizontal=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='card'><div class='card-title'>기록</div>", unsafe_allow_html=True)
            memo = st.text_input("특이사항/조치내용", value="이상 없음")
            staff = st.text_input("점검자 실명", placeholder="예: 홍길동")
            send_k_fac = st.checkbox("지점장에게 카카오 보고", value=False)
            save_db_fac = st.checkbox("DB에 저장", value=True)
            st.markdown("</div>", unsafe_allow_html=True)

        save = st.form_submit_button("기록 저장", use_container_width=True)

    if save:
        if not staff.strip():
            st.error("점검자 실명을 입력하십시오.")
            st.stop()

        ts = get_korea_timestamp()

        # 화면 표시용 드라이 로그
        log_text = (
            f"[FACILITY SAFETY LOG]\n"
            f"EVENT: {task}\n"
            f"TIMESTAMP: {ts}\n"
            f"LOCATION: {place}\n"
            f"ACTION: {memo.strip()}\n"
            f"STAFF: {staff.strip()}\n"
        )

        st.markdown("<div class='card'><div class='card-title'>저장 결과</div>", unsafe_allow_html=True)
        st.code(log_text, language="text")
        st.markdown("</div>", unsafe_allow_html=True)

        # DB 저장
        if save_db_fac:
            if not sheet:
                st.error("DB가 OFFLINE입니다. 시트 공유 권한 및 Secrets를 확인하십시오.")
            else:
                ok, err = safe_append_row(sheet, [ts, "FACILITY_LOG", task, place, memo.strip(), staff.strip()])
                if ok:
                    st.success("DB 저장 성공")
                else:
                    st.error(f"DB 저장 실패: {err}")

        # 카카오 보고
        if send_k_fac:
            msg = (
                f"[시설 점검 보고]\n"
                f"시간: {ts}\n"
                f"점검자: {staff.strip()}\n"
                f"유형: {task}\n"
                f"구역: {place}\n"
                f"내용: {memo.strip()}\n"
            )
            k_ok, k_err = send_kakao_message(msg)
            if k_ok:
                st.success("카카오 보고 성공")
            else:
                st.warning(f"카카오 보고 실패: {k_err}")
