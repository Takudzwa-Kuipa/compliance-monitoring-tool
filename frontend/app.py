import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Compliance Monitor", page_icon="🛡️", layout="wide")


for key in ["token", "role", "logged_in", "evaluation_results"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "logged_in" else False


def safe_request(method, url, **kwargs):
    res = requests.request(method, url, **kwargs)

    if res.status_code == 401:
        st.warning("Session expired. Please login again.")
        st.session_state.clear()
        st.rerun()

    return res


def login(username, password):
    res = requests.post(f"{API_URL}/login", data={"username": username, "password": password})

    if res.status_code == 200:
        data = res.json()
        st.session_state.token = data["access_token"]
        st.session_state.role = data["role"]
        st.session_state.logged_in = True
        st.success("Login successful")
        st.rerun()
    else:
        st.error("Invalid credentials")


def headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}



if not st.session_state.logged_in:
    st.title("🔐 Compliance Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        login(u, p)

    st.stop()



with st.sidebar:
    st.success(f"Logged in as: {st.session_state.role}")

    page = st.radio("Navigation", [
        "Dashboard",
        "Upload Evidence",
        "Evaluation",
        "Alerts",
        "Reports"
    ])

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()


st.title("🛡️ Compliance Monitoring System")


if page == "Dashboard":
    st.header("📊 Executive Dashboard")

    if st.session_state.evaluation_results:
        results = st.session_state.evaluation_results

        col1, col2, col3 = st.columns(3)
        col1.metric("Score", f"{results['score']}%")
        col2.metric("Compliant", results["compliant"])
        col3.metric("Failed", results["failed"])

        df = pd.DataFrame(results["details"])

        st.subheader("📊 Risk Distribution")
        fig = px.pie(df, names="risk", title="Risk Levels")
        st.plotly_chart(fig, use_container_width=True)

        # TABLE
        st.subheader("📄 Control Results")
        st.dataframe(df, use_container_width=True)

    else:
        st.info("Run evaluation to populate dashboard")



elif page == "Upload Evidence":
    st.header("📎 Smart Upload & Validation")

    file = st.file_uploader("Upload CSV", type=["csv"])

    if file:
        df = pd.read_csv(file)

        st.subheader("👀 Preview")
        st.dataframe(df.head(), use_container_width=True)

        st.subheader("📊 Columns")
        st.write(list(df.columns))

        with st.spinner("Validating dataset..."):
            res = requests.post(
                f"{API_URL}/validate-dataset",
                files={"file": file.getvalue()}
            )

        if res.status_code == 200:
            data = res.json()

            st.subheader("🧠 Detection")
            st.info(f"Framework: {data['detected_framework']}")

            if data["is_valid"]:
                st.success("✅ Valid dataset")

                if st.button("🚀 Upload & Auto Map"):
                    upload = safe_request(
                        "POST",
                        f"{API_URL}/upload-auto",
                        headers=headers(),
                        files={"file": file.getvalue()}
                    )

                    if upload.status_code == 200:
                        data = upload.json()

                        st.success(
                            f"Uploaded → {data.get('control')} "
                            f"(Framework: {data.get('framework')})"
                        )
                    else:
                        st.error(upload.text)

            else:
                st.error("❌ Missing fields")
                st.write(data["missing_fields"])



elif page == "Evaluation":
    st.header("⚙️ Run Evaluation")

    if st.button("Run Compliance Check"):
        with st.spinner("Evaluating..."):
            res = safe_request("POST", f"{API_URL}/evaluate-all", headers=headers())

        if res.status_code == 200:
            st.session_state.evaluation_results = res.json()
            st.success("Evaluation complete")
            st.rerun()


elif page == "Alerts":
    st.header("🚨 Alerts")

    alerts = safe_request("GET", f"{API_URL}/alerts", headers=headers()).json()

    if alerts:
        for a in alerts:
            if a["severity"] == "CRITICAL":
                st.error(a["message"])
            else:
                st.warning(a["message"])
    else:
        st.success("No alerts")


elif page == "Reports":
    st.header("📄 Executive Report")

    if st.button("Download PDF"):
        res = safe_request("GET", f"{API_URL}/download-report", headers=headers())

        with open("compliance_report.pdf", "wb") as f:
            f.write(res.content)

        st.success("Downloaded report.pdf")

elif page == "Trends":
    data = safe_request("GET", f"{API_URL}/trend").json()

    import pandas as pd
    df = pd.DataFrame(data)

    st.line_chart(df["status"].value_counts())

elif page == "Audit Logs":
    logs = safe_request("GET", f"{API_URL}/audit-logs").json()

    import pandas as pd
    st.dataframe(pd.DataFrame(logs), width="stretch")