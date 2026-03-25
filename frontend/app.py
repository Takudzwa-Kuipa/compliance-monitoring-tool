import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API = "http://localhost:8000"

st.set_page_config(layout="wide")

st.markdown("""
<style>

/* GLOBAL */
html, body {
    background: linear-gradient(135deg, #0E1117, #1a1f2b);
    font-family: 'Segoe UI', sans-serif;
    color: white;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
background: linear-gradient(180deg, #0e1117, #07080a);}

/* HEADER */
.header {
    display: flex;
    justify-content: space-between;
    background: rgba(255,255,255,0.05);
    padding: 15px 25px;
    border-radius: 20px;
    margin-bottom: 25px;
}

/* CARD */
.card {
    background: rgba(255,255,255,0.06);
    border-radius: 20px;
    padding: 20px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.4);
    transition: 0.3s;
}

.card:hover {
    transform: translateY(-5px);
}

/* METRIC */
.metric {
    font-size: 32px;
    font-weight: bold;
    color: #ff4d4d;
}

/* BUTTON */
.stButton button {
    background: linear-gradient(90deg, #ff1a1a, #ff4d4d);
    border-radius: 20px;
    color: white;
    border: none;
}

</style>
""", unsafe_allow_html=True)


st.sidebar.title("📊 Navigation")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "IT Operations", "Alerts"],
    label_visibility="collapsed"
)


st.markdown("""
<div class="header">
    <h2>🛡 Compliance Monitoring</h2>
    <div>🔍 User Profile</div>
</div>
""", unsafe_allow_html=True)


controls = requests.get(f"{API}/controls").json()
alerts = requests.get(f"{API}/alerts").json()

df = pd.DataFrame(controls)


if page == "Dashboard":

    st.title("📊 Executive Dashboard")

    total = len(df)

    col1, col2, col3 = st.columns(3)

    col1.markdown(f"""
    <div class="card">
        Total Controls
        <div class="metric">{total}</div>
    </div>
    """, unsafe_allow_html=True)

    col2.markdown("""
    <div class="card">
        Compliance Score
        <div class="metric">--%</div>
    </div>
    """, unsafe_allow_html=True)

    col3.markdown("""
    <div class="card">
        Risk Level
        <div class="metric">Medium</div>
    </div>
    """, unsafe_allow_html=True)

    # Alerts Section
    st.subheader("🚨 Alerts")

    col1, col2 = st.columns([4, 1])

    with col1:
        if alerts:
            for alert in alerts:
                st.error(f"{alert['message']} ({alert['severity']})")
        else:
            st.success("No active alerts")

    with col2:
        if st.button("🧹 Clear Alerts"):
            response = requests.delete(f"{API}/alerts")

            if response.status_code == 200:
                st.success("Alerts cleared!")
                st.rerun()
            else:
                st.error("Failed to clear alerts")


elif page == "IT Operations":

    st.title("🛠 IT Operations")

    st.dataframe(df, width='stretch')

    st.subheader("📎 Upload Evidence")

    control_id = st.selectbox(
        "Select Control",
        df["control_id"] if not df.empty else []
    )

    uploaded_file = st.file_uploader("Upload File")

    if uploaded_file is not None:
        files = {
            "file": (uploaded_file.name, uploaded_file.getvalue())
        }

        response = requests.post(
            f"{API}/evidence/{control_id}",
            files=files
        )

        if response.status_code == 200:
            st.success("Uploaded successfully")
        else:
            st.error("Upload failed")

# ============================
# 🚨 ALERTS PAGE
# ============================
elif page == "Alerts":

    st.title("🚨 Alerts Center")

    if alerts:
        for alert in alerts:
            st.error(f"{alert['message']} ({alert['severity']})")
    else:
        st.success("No alerts")

# ============================
# 🚀 RUN COMPLIANCE
# ============================
st.divider()

if st.button("Run Compliance Check"):

    with st.spinner("Running compliance engine..."):
        results = requests.get(f"{API}/evaluate").json()

    df_results = pd.DataFrame(results)

    st.subheader("📊 Compliance Results")

    st.dataframe(df_results, width='stretch')

    total = len(df_results)
    compliant = len(df_results[df_results["status"] == "COMPLIANT"])
    failed = len(df_results[df_results["status"] == "FAILED"])

    col1, col2, col3 = st.columns(3)

    col1.metric("Total", total)
    col2.metric("Compliant", compliant)
    col3.metric("Failed", failed)

    # Charts
    colA, colB = st.columns(2)

    with colA:
        fig = px.pie(df_results, names="status")
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, width='stretch')

    with colB:
        fig2 = px.histogram(df_results, x="status")
        fig2.update_layout(template="plotly_dark")
        st.plotly_chart(fig2, width='stretch')

    if failed > 0:
        st.error(f" {failed} controls failed")
    else:
        st.success(" All controls compliant")