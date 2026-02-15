import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import openai
import re

# -----------------------------------------------------------------------------
# 1. SYSTEM CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MAP SYSTEM vNext", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.main {background-color: #FFFFFF;}

.decision-box {
    padding: 25px;
    border-radius: 14px;
    text-align: center;
    font-size: 28px;
    font-weight: 800;
    margin: 20px 0;
}

.dec-stop {background:#FFEAEA; color:#B00020; border:3px solid #B00020;}
.dec-mod {background:#FFF6E5; color:#B26A00; border:3px solid #B26A00;}
.dec-go {background:#E8F5E9; color:#1B5E20; border:3px solid #1B5E20;}

.section-box {
    padding:20px;
    border-radius:12px;
    margin-top:15px;
    margin-bottom:15px;
}

.sec-internal {background:#F5F5F5;}
.sec-fsl {background:#FDF5E6;}
.sec-client {background:#FFF9C4;}

.small-note {
    font-size:0.85em;
    color:#777;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. UTIL
# -----------------------------------------------------------------------------
def kst():
    return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

def connect_db():
    try:
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        return client.open("MAP_DATABASE").sheet1
    except:
        return None

def extract_client_msg(text):
    match = re.search(r"### 3\..*?\n---(.*?)---", text, re.DOTALL)
    return match.group(1).strip() if match else text[:200]

# -----------------------------------------------------------------------------
# 3. CONNECT
# -----------------------------------------------------------------------------
sheet = connect_db()

if "OPENAI_API_KEY" in st.secrets:
    ai = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    ai = None

# -----------------------------------------------------------------------------
# 4. PROMPT (CORE)
# -----------------------------------------------------------------------------
MAP_CORE_PROMPT = """
You are a Non-medical Administrative Safety System.

PRIORITY:
1. Legal safety of center
2. Operational clarity
3. No emotional language

Return strictly this structure:

### 1. FSL REPORT
---
Decision: [STOP] / [MODIFICATION] / [GO]
Risk: (1 sentence biomechanical reason)
Restriction: (specific)
Alternative: (safe alternative)
Cue: (1 technical cue)
---

### 2. INTERNAL CHECK MATRIX
---
Red Flag: PASS/FAIL
Load Conflict: DIRECT/INDIRECT/NONE
Sanitization: APPLIED
---

### 3. CLIENT MESSAGE
---
Polite short message based on decision.
---
"""

# -----------------------------------------------------------------------------
# 5. MAIN UI
# -----------------------------------------------------------------------------
st.title("MAP SYSTEM vNext")
st.write(f"Time (KST): {kst()}")

tab1, tab2 = st.tabs(["PT Safety", "Facility Log"])

# =============================================================================
# TAB 1 - PT SAFETY
# =============================================================================
with tab1:

    with st.form("pt_form"):
        col1, col2 = st.columns(2)

        with col1:
            member = st.text_input("Member")
            symptom = st.text_input("Condition")
        with col2:
            exercise = st.text_input("Exercise")

        submit = st.form_submit_button("Run Analysis")

    if submit and ai and sheet:

        prompt = MAP_CORE_PROMPT + f"""

INPUT:
Member: {member}
Condition: {symptom}
Exercise: {exercise}
"""

        response = ai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"system","content":prompt}],
            temperature=0.2
        )

        result = response.choices[0].message.content

        # -----------------------
        # DECISION PARSE
        # -----------------------
        if "[STOP]" in result:
            decision = "STOP"
            css = "dec-stop"
        elif "[MODIFICATION]" in result:
            decision = "MODIFICATION"
            css = "dec-mod"
        else:
            decision = "GO"
            css = "dec-go"

        # -----------------------
        # DECISION BLOCK
        # -----------------------
        st.markdown(f"""
        <div class="decision-box {css}">
        {decision}
        </div>
        """, unsafe_allow_html=True)

        # -----------------------
        # FSL SECTION
        # -----------------------
        st.markdown('<div class="section-box sec-fsl">', unsafe_allow_html=True)
        st.markdown("### 1. FSL Administrative Report")
        st.markdown(result.split("### 2.")[0])
        st.markdown("</div>", unsafe_allow_html=True)

        # -----------------------
        # INTERNAL MATRIX
        # -----------------------
        internal = re.search(r"### 2\..*?---(.*?)---", result, re.DOTALL)
        if internal:
            st.markdown('<div class="section-box sec-internal">', unsafe_allow_html=True)
            st.markdown("### 2. Internal Check Matrix")
            st.text(internal.group(1).strip())
            st.markdown("</div>", unsafe_allow_html=True)

        # -----------------------
        # CLIENT MESSAGE
        # -----------------------
        client_msg = extract_client_msg(result)
        st.markdown('<div class="section-box sec-client">', unsafe_allow_html=True)
        st.markdown("### 3. Client Message Preview")
        st.markdown(client_msg)
        st.markdown("</div>", unsafe_allow_html=True)

        # -----------------------
        # DB SAVE
        # -----------------------
        sheet.append_row([
            kst(),
            "PT_ANALYSIS",
            member,
            symptom,
            exercise,
            decision
        ])

# =============================================================================
# TAB 2 - FACILITY LOG
# =============================================================================
with tab2:

    with st.form("fac_form"):
        col1, col2 = st.columns(2)

        with col1:
            task = st.selectbox("Task",
                                ["Patrol", "Fix", "Clean", "Other"])
            zone = st.selectbox("Zone",
                                ["Weight", "Cardio", "Locker", "Free"])
        with col2:
            memo = st.text_input("Note")
            staff = st.text_input("Staff")

        save = st.form_submit_button("Save Log")

    if save and sheet:
        sheet.append_row([
            kst(),
            "FACILITY",
            task,
            zone,
            memo,
            staff
        ])

        st.success("Log saved.")
