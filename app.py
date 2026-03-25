import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from io import BytesIO
import plotly.express as px

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Enterprise Compliance Dashboard", layout="wide")

st.markdown("""
<style>
body {background: linear-gradient(135deg, #0E1117, #1a1f2b); color: white;}

.card {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(12px);
    padding: 20px;
    border-radius: 15px;
    margin-bottom: 20px;
}

.metric {font-size: 30px; font-weight: bold; color: #ff4d4d;}

[data-testid="stSidebar"] {background: linear-gradient(180deg, #ff2b2b, #990000);}

.badge {padding: 6px 12px; border-radius: 10px; font-weight: bold;}

.critical {background: #ff1a1a;}
.high {background: #ff6600;}
.medium {background: #ffcc00; color:black;}
.low {background: #33cc33;}

/* MTTR */
.mttr-container {display:flex; justify-content:space-around; margin-top:20px;}
.mttr-bar {width:60px; height:150px; border-radius:30px; background:rgba(255,255,255,0.1); display:flex; align-items:flex-end;}
.mttr-fill {width:100%; border-radius:30px;}
.low-bar {height:30%; background:#ffb3b3;}
.medium-bar {height:60%; background:#ff6666;}
.high-bar {height:90%; background:#ff1a1a;}
</style>
""", unsafe_allow_html=True)

USERS = {
    "admin": {"password": "admin", "role": "Admin"},
    "risk": {"password": "risk", "role": "Risk"},
    "audit": {"password": "audit", "role": "Audit"}
}

def login():
    st.sidebar.title("🔐 Login")
    u = st.sidebar.text_input("Username")
    p = st.sidebar.text_input("Password", type="password")
    if u in USERS and USERS[u]["password"] == p:
        return USERS[u]["role"]
    elif u and p:
        st.sidebar.error("Invalid credentials")
    return None

role = login()
if not role:
    st.stop()

def load_data():
    file = "evidence_files/compliance_large_dataset.csv"
    if os.path.exists(file):
        df = pd.read_csv(file)
        df.columns = df.columns.str.lower().str.strip()
        return df
    else:
        st.error("Dataset not found")
        return pd.DataFrame()

df = load_data()

# ============================
#  FILTERS
# ============================
st.sidebar.title("Filters")

if "framework" in df.columns:
    fw = st.sidebar.selectbox("Framework", ["All"] + list(df["framework"].unique()))
    if fw != "All":
        df = df[df["framework"] == fw]

if "department" in df.columns:
    dept = st.sidebar.selectbox("Department", ["All"] + list(df["department"].unique()))
    if dept != "All":
        df = df[df["department"] == dept]

# ============================
# CALCULATIONS
# ============================
df["risk score"] = pd.to_numeric(df["risk score"], errors="coerce").fillna(0)

def classify_risk(x):
    if x >= 8: return "Critical"
    elif x >= 6: return "High"
    elif x >= 4: return "Medium"
    return "Low"

df["risk_level"] = df["risk score"].apply(classify_risk)

df["mttr days"] = pd.to_numeric(df["mttr days"], errors="coerce")
df["sla days"] = pd.to_numeric(df["sla days"], errors="coerce")
df["sla_breach"] = df["mttr days"] > df["sla days"]

def compliance_score(df):
    total = len(df)
    completed = len(df[df["status"].str.lower()=="completed"])
    progress = len(df[df["status"].str.lower()=="in progress"])
    return round(((completed + 0.5*progress)/total)*100,2)

compliance = compliance_score(df)
var_score = round(np.percentile(df["risk score"],95),2)

# Framework scores
def framework_scores(df):
    res={}
    for fw in df["framework"].unique():
        subset=df[df["framework"]==fw]
        res[fw]=compliance_score(subset)
    return res

fw_scores = framework_scores(df)

# ============================
# ALERTS
# ============================
LOW=80
CRIT=60

st.subheader("🚨 Alerts")

if compliance < CRIT:
    st.error("Critical Compliance Risk")
elif compliance < LOW:
    st.warning("Compliance Warning")
else:
    st.success("Compliance Healthy")

for k,v in fw_scores.items():
    if v < CRIT:
        st.error(f"{k} Critical ({v}%)")
    elif v < LOW:
        st.warning(f"{k} Warning ({v}%)")


c1,c2,c3,c4 = st.columns(4)
c1.metric("VaR", var_score)
c2.metric("Compliance", f"{compliance}%")
c3.metric("Controls", len(df))
c4.metric("SLA Breaches", len(df[df["sla_breach"]]))

# ============================
# Framework Scores
# ============================
st.subheader("Framework Compliance")
st.bar_chart(pd.DataFrame(fw_scores.values(), index=fw_scores.keys()))

# ============================
# Charts
# ============================
col1,col2=st.columns(2)

with col1:
    st.plotly_chart(px.histogram(df,x="risk score"))

with col2:
    trend=df.copy()
    trend["date"]=pd.date_range(end=pd.Timestamp.today(), periods=len(df))
    st.plotly_chart(px.line(trend,x="date",y="risk score"))

# ============================
# Heatmap
# ============================
heat=df.groupby(["department","risk_level"]).size().unstack(fill_value=0)
st.plotly_chart(px.imshow(heat,text_auto=True))

# ============================
# MTTR VISUAL
# ============================
st.subheader("MTTR Visual")

b1=len(df[df["mttr days"]<=7])
b2=len(df[(df["mttr days"]>7)&(df["mttr days"]<=14)])
b3=len(df[df["mttr days"]>14])

st.markdown(f"""
<div class="mttr-container">
<div><div class="mttr-bar"><div class="mttr-fill low-bar"></div></div>1-7<br>{b1}</div>
<div><div class="mttr-bar"><div class="mttr-fill medium-bar"></div></div>8-14<br>{b2}</div>
<div><div class="mttr-bar"><div class="mttr-fill high-bar"></div></div>15-30<br>{b3}</div>
</div>
""", unsafe_allow_html=True)

# ============================
# Control Evidence
# ============================
st.subheader("Control → Evidence")
st.dataframe(df[["control","control description","evidence"]].head(20))

# ============================
# PDF REPORT
# ============================
def generate_pdf():
    buffer=BytesIO()
    doc=SimpleDocTemplate(buffer)
    styles=getSampleStyleSheet()
    elements=[Paragraph("Compliance Report",styles["Title"])]
    doc.build(elements)
    buffer.seek(0)
    return buffer

if st.button("Generate PDF"):
    st.download_button("Download", generate_pdf())