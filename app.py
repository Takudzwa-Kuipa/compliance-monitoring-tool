import streamlit as st
from datetime import datetime
import os
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO


st.set_page_config(page_title="Compliance Dashboard", layout="wide")


# st.markdown("""
# <style>
# body {background-color: #0E1117;}
#
# [data-testid="stSidebar"] {
#     background-color: #ff2b2b;
# }
#
# .metric-box {
#     background-color: #1c1f26;
#     padding: 20px;
#     border-radius: 15px;
#     text-align: center;
# }
# </style>
# """, unsafe_allow_html=True)


def login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if username == "admin" and password == "admin":
        return True
    elif username and password:
        st.sidebar.error("Invalid credentials")
    return False


if not login():
    st.stop()



def load_excel():
    file = os.path.join("evidence_files", "Integrated_Compliance_Control_Model_With_Ownership (1).xlsx")
    if os.path.exists(file):
        return pd.read_excel(file)
    return pd.DataFrame()


# -----------------------------
# AUTO COLUMN DETECTION
# -----------------------------
def detect_column(df, names):
    for col in df.columns:
        if col.lower().strip() in names:
            return col
    return None


# -----------------------------
# ADVANCED METRICS FUNCTION
# -----------------------------
def calculate_metrics(df):

    if df.empty:
        return 0, 0

    df.columns = df.columns.str.strip()

    status_col = detect_column(df, ["status", "task_status", "control_status"])
    risk_col = detect_column(df, ["risk_score", "risk", "risk level"])

    # Normalize status
    if status_col:
        df[status_col] = df[status_col].astype(str).str.lower().str.strip()

    # -------------------
    # ADVANCED COMPLIANCE
    # -------------------
    compliance = 0

    if status_col:
        total = len(df)

        completed = len(df[df[status_col].isin(["completed", "done", "closed"])])
        partial = len(df[df[status_col].isin(["in progress", "ongoing"])])
        failed = len(df[df[status_col].isin(["failed", "overdue"])])

        # Weighted scoring
        compliance_score = (
            (completed * 1.0) +
            (partial * 0.5) +
            (failed * 0.0)
        )

        compliance = round((compliance_score / total) * 100, 2)

    # -------------------
    # RISK SCORE
    # -------------------
    risk = 0

    if risk_col:
        risk = pd.to_numeric(df[risk_col], errors="coerce").fillna(0).sum()
    elif status_col:
        for status in df[status_col]:
            if status in ["pending", "open", "in progress"]:
                risk += 5
            elif status in ["failed", "overdue"]:
                risk += 10

    return compliance, int(risk)


# -----------------------------
# REPORT FUNCTION
# -----------------------------
def generate_report(score, risk):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    content = [
        Paragraph("<b>Compliance Report</b>", styles["Title"]),
        Paragraph(f"Compliance Score: {score}%", styles["Normal"]),
        Paragraph(f"Risk Score: {risk}", styles["Normal"]),
        Paragraph(f"Generated: {datetime.now()}", styles["Normal"])
    ]

    doc.build(content)
    buffer.seek(0)
    return buffer


excel_data = load_excel()
score, risk = calculate_metrics(excel_data)


# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("Compliance System")
page = st.sidebar.radio("Navigation", [
    "Dashboard",
    "Data View",
    "Reports"
])


# =============================
# DASHBOARD
# =============================
if page == "Dashboard":

    st.title("🏦 Executive Compliance Dashboard")

    col1, col2, col3 = st.columns(3)

    col1.markdown(f'<div class="metric-box">📋 Controls<br><h2>{len(excel_data)}</h2></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-box">📈 Compliance<br><h2>{score}%</h2></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-box">⚠️ Risk Score<br><h2>{risk}</h2></div>', unsafe_allow_html=True)

    st.divider()

    status_col = detect_column(excel_data, ["status", "task_status", "control_status"])
    framework_col = detect_column(excel_data, ["framework"])
    owner_col = detect_column(excel_data, ["owner"])

    colA, colB = st.columns(2)

    with colA:
        st.subheader("📊 Task Status")
        if status_col:
            st.bar_chart(excel_data[status_col].value_counts())

    with colB:
        st.subheader("🎯 Framework Breakdown")
        if framework_col:
            st.bar_chart(excel_data[framework_col].value_counts())

    st.divider()

    if owner_col:
        st.subheader("👤 Ownership")
        st.bar_chart(excel_data[owner_col].value_counts())

    st.divider()

    st.subheader("🔔 Notifications")

    st.markdown("""
    <div style="background-color:#5c1f1f; padding:15px; border-radius:10px; margin-bottom:10px;">
        🔴 <b>Critical:</b> High-risk controls detected
    </div>

    <div style="background-color:#5a5c1f; padding:15px; border-radius:10px; margin-bottom:10px;">
        🟡 <b>Warning:</b> Pending compliance tasks
    </div>

    <div style="background-color:#1f3c5c; padding:15px; border-radius:10px;">
        🔵 <b>Info:</b> Monitoring ongoing
    </div>
    """, unsafe_allow_html=True)


# =============================
# DATA VIEW
# =============================
elif page == "Data View":

    st.title("📊 Full Dataset")

    if not excel_data.empty:
        st.dataframe(excel_data)
    else:
        st.warning("Excel file not found")


# =============================
# REPORTS
# =============================
elif page == "Reports":

    st.title("📄 Generate Report")

    if st.button("Generate PDF"):
        pdf = generate_report(score, risk)

        st.download_button(
            label="📥 Download Report",
            data=pdf,
            file_name="compliance_report.pdf",
            mime="application/pdf"
        )