


import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="파일 추적기", layout="wide")
st.title("🕵️‍♂️ 구글 시트 위치 추적기")

def find_ghost_sheet():
    # 1. 연결 시도
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]), scope
        )
        client = gspread.authorize(creds)
        
        # 2. 파일 열기
        doc = client.open("MAP_DATABASE") # AI가 보고 있는 파일
        sheet = doc.sheet1
        
        return doc, sheet, None
    except Exception as e:
        return None, None, str(e)

# 추적 시작
doc, sheet, error = find_ghost_sheet()

if error:
    st.error(f"❌ 연결 실패! 원인: {error}")
else:
    # 3. 범인 색출 결과 (화면에 대문짝만하게 링크 띄우기)
    st.success("✅ AI가 몰래 쓰고 있던 '진짜 파일'을 찾았습니다!")
    
    real_url = f"https://docs.google.com/spreadsheets/d/{doc.id}"
    
    st.markdown(f"""
    ## 👇 아래 링크를 클릭하세요! (여기가 진짜입니다)
    # [👉 [클릭] AI가 작성 중인 엑셀 파일 열기]({real_url})
    """)
    
    st.divider()
    
    # 4. 증거물 제시 (최근 데이터 읽어오기)
    st.subheader("📋 최근 기록된 데이터 (증거물)")
    try:
        data = sheet.get_all_values()
        if len(data) > 0:
            st.write(f"총 {len(data)}개의 데이터가 발견되었습니다.")
            st.dataframe(data[-5:]) # 뒤에서 5개만 보여줌
        else:
            st.warning("파일은 찾았는데, 내용은 비어있습니다.")
            
            # 테스트 데이터 강제 주입
            if st.button("강제로 데이터 한 줄 써보기"):
                sheet.append_row(["추적성공", "지금", "여기가", "진짜", "파일입니다"])
                st.toast("데이터 전송 완료! 위 링크를 다시 눌러보세요.")
                st.rerun()
    except Exception as e:
        st.error(f"데이터 읽기 실패: {e}")
