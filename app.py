import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import re

# -----------------------------------------------------------------------------
# 1. 시스템 설정 & 스타일 (가독성 패치 적용)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .main {background-color: #0E1117;}
    
    /* 결과 박스 공통 디자인 (글씨 흰색 강제 적용) */
    .result-box {
        padding: 25px; 
        border-radius: 12px; 
        margin: 15px 0; 
        border: 1px solid #555;
        color: #e0e0e0 !important; /* 기본 글씨 밝은 회색 */
        line-height: 1.6;
        font-size: 1.05em;
    }
    
    /* 제목, 강조 텍스트는 완전 흰색으로 */
    .result-box h1, .result-box h2, .result-box h3, .result-box strong, .result-box b {
        color: #ffffff !important;
        font-weight: 700;
    }

    /* 상태별 배경색 (너무 어둡지 않게 조정) */
    .res-stop {background-color: #2d1212; border-left: 6px solid #ff4b4b;} 
    .res-mod {background-color: #2d240b; border-left: 6px solid #ffa425;}
    .res-go {background-color: #0f2615; border-left: 6px solid #00cc44;}

    /* 카카오톡 템플릿 영역 강조 */
    .kakao-area {
        background-color: #383838;
        padding: 15px;
        border-radius: 8px;
        margin-top: 10px;
        border: 1px dashed #777;
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
        return "카톡 메시지 자동 생성 실패 (원문 참조)"
    except: return full_text[:100]

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
