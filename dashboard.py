import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# ---------------------------------------------------------
# [구글 시트 데이터 로드]
# ---------------------------------------------------------
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("MAP_DATABASE").sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# 1. 페이지 설정
st.set_page_config(page_title="MAP HQ DASHBOARD", page_icon="🏢", layout="wide")
st.title("🏢 MAP ENTERPRISE : 통합 관제 센터")

# 2. 데이터 불러오기 (새로고침 버튼)
if st.button("🔄 데이터 최신화"):
    st.rerun()

try:
    df = load_data()
    
    # 데이터가 비어있을 경우 방지
    if df.empty:
        st.warning("아직 데이터가 없습니다.")
        st.stop()

    # 날짜 형식 변환
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])

    # 3. KPI 지표
    total_logs = len(df)
    today_logs = len(df[df['Timestamp'].dt.date == datetime.now().date()])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("총 누적 데이터", f"{total_logs}건")
    col2.metric("오늘 점검 횟수", f"{today_logs}건", "실시간 집계")
    col3.metric("가동 지점", f"{df['Branch'].nunique()}곳")

    st.markdown("---")

    # 4. 지점별 최신 상태 (신호등 로직)
    st.subheader("📡 지점별 실시간 안전 신호등")
    
    branches = ["킹스짐 1호점 (본점)", "킹스짐 2호점", "킹스짐 3호점"]
    cols = st.columns(3)

    for i, branch in enumerate(branches):
        with cols[i]:
            # 해당 지점의 가장 최근 로그 가져오기
            branch_logs = df[df['Branch'] == branch].sort_values(by='Timestamp', ascending=False)
            
            if branch_logs.empty:
                st.error(f"🚨 {branch}")
                st.caption("데이터 없음 (즉시 확인 요망)")
            else:
                last_log = branch_logs.iloc[0]
                last_time = last_log['Timestamp']
                time_diff = datetime.now() - last_time
                
                # 3시간 이내 점검 없으면 빨간불
                if time_diff > timedelta(hours=3):
                    st.error(f"🚨 {branch}")
                    st.markdown(f"**상태: 위험 (점검 누락)**")
                    st.caption(f"마지막 점검: {last_time.strftime('%H:%M')} ({int(time_diff.total_seconds()/60)}분 전)")
                else:
                    st.success(f"✅ {branch}")
                    st.markdown(f"**상태: 정상 가동 중**")
                    st.caption(f"마지막 점검: {last_time.strftime('%H:%M')} ({int(time_diff.total_seconds()/60)}분 전)")
                    st.text(f"담당자: {last_log['Staff']}")

    # 5. 상세 데이터
    with st.expander("📜 전체 로그 데이터 확인"):
        st.dataframe(df.sort_values(by='Timestamp', ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    st.info("구글 시트 설정(service_account.json)을 확인해주세요.")