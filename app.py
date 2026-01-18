import streamlit as st

st.set_page_config(
    page_title="MAP SYSTEM",
    page_icon="🛡️",
    layout="centered"
)

st.title("🛡️ MAP SYSTEM")
st.subheader("센터 · 트레이너 · 관장을 보호하는 안전 관리 시스템")

st.markdown("""
이 페이지는 **MAP SYSTEM 베타 앱**입니다.

- 트레이너는 로그인 없이 사용
- 수업 전 최소 입력으로 관리 기록 생성
- 법적 분쟁 대응을 위한 로그 기반 구조
""")

st.success("✅ MAP SYSTEM이 정상적으로 실행되었습니다.")
