# ---------------------------
# 판정 파싱 (안정화)
# ---------------------------
def extract_decision(text: str):
    t = text.upper()
    if "STOP" in t:
        return "STOP"
    if "MODIFICATION" in t:
        return "MODIFICATION"
    return "GO"


# ---------------------------
# 카카오 메시지 추출 (안정)
# ---------------------------
def extract_kakao_message(text):
    if "카카오" in text:
        return text.split("카카오")[1][:500]
    return text[:300]


# ---------------------------
# OpenAI 호출 (정석 구조)
# ---------------------------
input_block = f"""
[INPUT]
Member: {member}
Symptom: {final_symptom}
Exercise: {exercise}
"""

response = ai_client.chat.completions.create(
    model="gpt-4o",
    temperature=0.2,
    messages=[
        {"role": "system", "content": MAP_CORE_PROMPT},
        {"role": "user", "content": input_block}
    ]
)

full_res = response.choices[0].message.content
decision = extract_decision(full_res)


# ---------------------------
# 결과 UI (가독성 강화)
# ---------------------------
css_map = {
    "STOP": "res-stop",
    "MODIFICATION": "res-mod",
    "GO": "res-go"
}

st.markdown(
    f"""
    <div class="result-box {css_map[decision]}">
        <h3>판정 결과: {decision}</h3>
        <hr/>
        {full_res}
    </div>
    """,
    unsafe_allow_html=True
)


# ---------------------------
# DB 저장 (변경 없음 – 매우 좋음)
# ---------------------------
ok, err = safe_append_row(
    sheet,
    [
        get_korea_timestamp(),
        "PT_CORE_ANALYSIS",
        member,
        final_symptom,
        exercise,
        decision,
        full_res[:4000]
    ]
)
