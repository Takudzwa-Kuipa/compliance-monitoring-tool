import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import json

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Compliance Monitor",
    page_icon="🛡️",
    layout="wide"
)

if "evaluation_results" not in st.session_state:
    st.session_state.evaluation_results = None

st.title("🛡️ Compliance Monitoring System")

# Sidebar
with st.sidebar:
    st.header(" Navigation")
    page = st.radio("Go to", ["Dashboard", "Upload Files", "Evaluation Results", "Alerts"])

    st.divider()

    # API Status
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        if response.status_code == 200:
            st.success(" API Connected")
        else:
            st.error(" API Error")
    except:
        st.error(" API Not Running")
        st.info("Start backend: uvicorn main:app --reload")

# Main content
if page == "Dashboard":
    st.header("📊 Compliance Dashboard")

    # Get statistics
    try:
        stats = requests.get(f"{API_URL}/statistics").json()
        score = requests.get(f"{API_URL}/compliance-score").json()
        alerts = requests.get(f"{API_URL}/alerts").json()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Controls", stats.get("total_controls", 0))
        with col2:
            st.metric("Evidence Files", stats.get("evidence_files", 0))
        with col3:
            st.metric("Compliance Score", f"{score.get('compliance_score', 0)}%")
        with col4:
            st.metric("Active Alerts", len(alerts))

        st.divider()

        # Run evaluation button
        if st.button(" Run Complete Compliance Check", type="primary", use_container_width=True):
            with st.spinner("Evaluating all controls..."):
                response = requests.post(f"{API_URL}/evaluate-all")
                if response.status_code == 200:
                    st.session_state.evaluation_results = response.json()
                    st.success("Evaluation complete!")
                    st.rerun()
                else:
                    st.error("Evaluation failed")

    except Exception as e:
        st.error(f"Error connecting to API: {e}")

elif page == "Upload Files":
    st.header("📎 Upload Evidence Files")

    tab1, tab2 = st.tabs(["Single File Upload", "Batch Upload"])

    with tab1:
        st.subheader("Upload for Specific Control")

        # Get controls
        controls = requests.get(f"{API_URL}/controls").json()
        if controls:
            control_options = {c["control_id"]: f"{c['control_id']} - {c['framework']}" for c in controls}
            selected_control = st.selectbox("Select Control", list(control_options.keys()),
                                            format_func=lambda x: control_options[x])

            uploaded_file = st.file_uploader(
                "Choose file",
                type=['csv', 'xlsx', 'xls', 'json', 'pdf', 'txt'],
                key="single_upload"
            )

            if uploaded_file and st.button("Upload"):
                files = {"file": uploaded_file}
                response = requests.post(f"{API_URL}/evidence/{selected_control}", files=files)

                if response.status_code == 200:
                    st.success(f" File uploaded successfully for {selected_control}")
                    st.json(response.json())
                else:
                    st.error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")
        else:
            st.warning("No controls found")

    with tab2:
        st.subheader("Batch Upload Multiple Files")
        st.info("Upload multiple files at once. The system will auto-detect control IDs from filenames.")

        uploaded_files = st.file_uploader(
            "Choose multiple files",
            type=['csv', 'xlsx', 'xls', 'json', 'pdf', 'txt'],
            accept_multiple_files=True,
            key="batch_upload"
        )

        if uploaded_files and st.button("Upload All Files"):
            files = [("files", file) for file in uploaded_files]
            response = requests.post(f"{API_URL}/evidence/batch", files=files)

            if response.status_code == 200:
                result = response.json()
                st.success(f" Uploaded {len(result.get('files', []))} files")
                for f in result.get('files', []):
                    st.info(f" {f['file_name']} → Control: {f['control_id']}")
            else:
                st.error("Batch upload failed")

elif page == "Evaluation Results":
    st.header(" Compliance Evaluation Results")

    # Button to run evaluation
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button(" Run Evaluation", type="primary"):
            with st.spinner("Evaluating..."):
                response = requests.post(f"{API_URL}/evaluate-all")
                if response.status_code == 200:
                    st.session_state.evaluation_results = response.json()
                    st.success("Evaluation complete!")
                else:
                    st.error("Evaluation failed")

    # Display results
    if st.session_state.evaluation_results:
        results = st.session_state.evaluation_results

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Evaluated", results.get("total", 0))
        with col2:
            st.metric("Compliant", results.get("compliant", 0), delta="")
        with col3:
            st.metric("Failed", results.get("failed", 0), delta="")
        with col4:
            score = results.get("compliance_score", 0)
            color = "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"
            st.metric("Score", f"{score}% {color}")

        st.divider()

        # Detailed results
        st.subheader("Detailed Results")

        for result in results.get("results", []):
            status = result["status"]
            if status == "COMPLIANT":
                with st.expander(f" {result['control']} - {result['framework']}"):
                    st.success(f"**Reason:** {result['reason']}")
                    if result.get('details'):
                        st.json(result['details'])
            else:
                with st.expander(f" {result['control']} - {result['framework']}", expanded=True):
                    st.error(f"**Reason:** {result['reason']}")
                    if result.get('details'):
                        st.json(result['details'])

        # Charts
        if results.get("results"):
            df = pd.DataFrame(results["results"])
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(df, names="status", title="Compliance Distribution", color="status",
                             color_discrete_map={"COMPLIANT": "#00ff88", "FAILED": "#ff4444"})
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(df, x="control", y="status", title="Control Status", color="status",
                             color_discrete_map={"COMPLIANT": "#00ff88", "FAILED": "#ff4444"})
                fig.update_layout(template="plotly_dark", xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Click 'Run Evaluation' to check compliance of uploaded files")

elif page == "Alerts":
    st.header(" Alerts")

    alerts = requests.get(f"{API_URL}/alerts").json()

    if alerts:
        st.warning(f" {len(alerts)} Active Alerts")

        for alert in alerts:
            with st.container():
                st.error(f"**{alert['severity']}** - {alert['message']}")
                if alert.get('control_id'):
                    st.caption(f"Control: {alert['control_id']}")
                st.caption(f"Time: {alert['created_at'][:19] if alert.get('created_at') else 'N/A'}")
                st.divider()

        if st.button("🗑️ Clear All Alerts"):
            response = requests.delete(f"{API_URL}/alerts")
            if response.status_code == 200:
                st.success("All alerts cleared")
                st.rerun()
    else:
        st.success(" No active alerts")

# Footer
st.divider()
st.caption("🔒Enterprise Compliance Management System | Supports CSV, Excel, JSON, PDF, TXT")