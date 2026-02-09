import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import requests
import re

# -----------------------------------------------------------------------------
# 1. 시스템 설정 & 대시보드 스타일링
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP INTEGRATED SYSTEM", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    /* 전체 배경 및 폰트 */
    .main {background-color: #0E1117;}
    
    /* 입력 폼 카드 디자인 */
    .stForm {
        background-color: #1A1C24;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* 결과 박스 디자인 (가독성 UP) */
    .result-box {
        padding: 25px; 
        border-radius: 12px; 
        margin-top: 20px; 
        margin-bottom: 20px;
        border: 1px solid #555;
        color: #ffffff !important;
        line-height: 1.6;
        font-size: 1.1em;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    
    /* 상태별 컬러 테마 */
    .res-stop {background: linear-gradient(135deg, #2d1212 0%, #4a0e0e 100%); border-left: 8px solid #ff4b4b;} 
    .res-mod {background: linear-gradient(135deg, #2d240b 0%, #4a3b0e 100%); border-left: 8px solid #ffa425;}
    .res-go {background: linear-gradient(135deg, #0f2615 0%, #0e4a1c 100%); border-left: 8px solid #00cc44;}

    /* 강조 텍스트 */
    .result-box h1, .result-box h2, .result-box h3, .result-box strong {
        color: #ffffff !important;
        text-shadow: 0px 0px 10px rgba(0,0,0,0.5);
    }

    /* 카톡 영역 */
    .kakao-area {
        background-color: #FEE500;
        color: #3b1e1e !important;
        padding: 15px;
        border-radius: 10px;
        margin-top: 15px;
        font-size: 0.9em;
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
        data = {"template_object": str({"object_type": "text", "text": text, "link
