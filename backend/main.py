from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import shutil, os, json
from datetime import datetime
import pandas as pd

from database import SessionLocal, engine as db_engine, Base
from models import Control, Evidence, ComplianceStatus, Alert, User
from compliance_engine import engine as compliance_engine
from auth.security import require_role, authenticate_user, create_access_token

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

Base.metadata.create_all(bind=db_engine)

app = FastAPI(title="Compliance Monitoring System", version="6.0")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


FRAMEWORK_SIGNATURES = {
    "HIPAA": {"patient_id", "record_date", "access_type", "user_id"},
    "PCI-DSS": {"transaction_id", "amount", "card_last4", "timestamp"},
    "NIST": {"event_id", "timestamp", "event_type", "source_ip"},
}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def clean_json(data):
    import numpy as np
    if isinstance(data, dict):
        return {k: clean_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_json(i) for i in data]
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        return float(data)
    return data


def calculate_risk(status, details):
    if status == "FAILED":
        return "HIGH"
    if isinstance(details, dict) and ("missing_columns" in details or "null_counts" in details):
        return "MEDIUM"
    return "LOW"


def classify_issue(details):
    if not isinstance(details, dict):
        return "GENERAL"

    if "missing_columns" in details:
        return "DATA_QUALITY"
    if "negative_count" in details:
        return "DATA_VALIDATION"
    if "null_counts" in details:
        return "DATA_COMPLETENESS"

    return "GENERAL"

def extract_issue_count(details):
    if not isinstance(details, dict):
        return 0

    return (
        details.get("negative_count", 0)
        or details.get("missing_count", 0)
        or details.get("null_count", 0)
        or 0
    )


AUDIT_LOG = []

def log_action(user, action, detail):
    AUDIT_LOG.append({
        "user": user.username if user else "system",
        "action": action,
        "detail": detail,
        "time": datetime.utcnow().isoformat()
    })


def detect_framework(df):
    cols = set(df.columns.str.lower())
    for fw, req in FRAMEWORK_SIGNATURES.items():
        if req.issubset(cols):
            return fw
    return "UNKNOWN"


@app.post("/validate-dataset")
def validate_dataset(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    cols = set(df.columns.str.lower())

    detected = "UNKNOWN"
    required = set()

    for fw, req in FRAMEWORK_SIGNATURES.items():
        if req.issubset(cols):
            detected = fw
            required = req
            break

    missing = list(required - cols) if required else []
    completeness = round((len(cols & required) / len(required)) * 100, 2) if required else 0

    return {
        "detected_framework": detected,
        "missing_fields": missing,
        "completeness": completeness,
        "is_valid": len(missing) == 0
    }


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")

    return {
        "access_token": create_access_token({"sub": user.username}),
        "role": user.role
    }


@app.post("/upload-auto")
def upload_auto(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN", "AUDITOR"]))
):
    path = os.path.join(UPLOAD_DIR, f"{datetime.now().timestamp()}_{file.filename}")

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    df = pd.read_csv(path)
    fw = detect_framework(df)

    if fw == "UNKNOWN":
        os.remove(path)
        raise HTTPException(400, "Unknown dataset")

    control = db.query(Control).filter(Control.framework == fw).first()

    db.query(Evidence).filter(Evidence.control_id == control.control_id).delete()

    db.add(Evidence(control_id=control.control_id, file_path=path, file_name=file.filename))
    db.commit()

    log_action(user, "UPLOAD", f"{file.filename} → {fw}")

    return {
        "framework": fw,
        "control": control.control_id
    }


@app.post("/evaluate-all")
def evaluate_all(
    db: Session = Depends(get_db),
    user=Depends(require_role(["ADMIN"]))
):
    db.query(ComplianceStatus).delete()
    db.query(Alert).delete()

    controls = db.query(Control).all()
    results, detailed = [], []

    for c in controls:
        ev = db.query(Evidence).filter(Evidence.control_id == c.control_id).first()

        status, reason, details = compliance_engine.evaluate_file(c, ev)

        details = clean_json(details)
        risk = calculate_risk(status, details)

        db.add(ComplianceStatus(
            control_id=c.control_id,
            status=status,
            risk=risk,
            reason=reason,
            details=json.dumps(details)
        ))

        if status == "FAILED":
            issue_type = classify_issue(details)
            issue_count = extract_issue_count(details)

            message = f"{c.control_id} FAILED | {risk} risk"

            if issue_count > 0:
                message += f" | {issue_count} records affected"

            db.add(Alert(
                control_id=c.control_id,
                message=message,
                severity="CRITICAL" if risk == "HIGH" else "WARNING"
            ))

        results.append(status)

        detailed.append({
            "control": c.control_id,
            "status": status,
            "risk": risk
        })

    db.commit()

    total = len(results)
    compliant = results.count("COMPLIANT")
    failed = results.count("FAILED")

    score = round((compliant / total) * 100, 2) if total else 0

    log_action(user, "EVALUATE", f"Score {score}%")

    return {
        "score": score,
        "total_controls": total,
        "compliant": compliant,
        "failed": failed,
        "details": detailed
    }


@app.get("/alerts")
def alerts(db: Session = Depends(get_db)):
    return db.query(Alert).all()

@app.get("/alerts-summary")
def alerts_summary(db: Session = Depends(get_db)):
    alerts = db.query(Alert).all()

    summary = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}

    for a in alerts:
        if a.severity in summary:
            summary[a.severity] += 1

    return summary

@app.get("/alerts-by-control/{control_id}")
def alerts_by_control(control_id: str, db: Session = Depends(get_db)):
    return db.query(Alert).filter(Alert.control_id == control_id).all()


@app.get("/trend")
def trend(db: Session = Depends(get_db)):
    data = db.query(ComplianceStatus).all()

    return [
        {
            "time": d.evaluated_at.isoformat(),
            "status": d.status
        }
        for d in data
    ]


@app.get("/audit-logs")
def audit_logs():
    return AUDIT_LOG


@app.get("/download-report")
def report(db: Session = Depends(get_db)):
    data = db.query(ComplianceStatus).all()

    path = "report.pdf"
    doc = SimpleDocTemplate(path)
    styles = getSampleStyleSheet()

    content = [Paragraph("Compliance Report", styles["Title"]), Spacer(1, 20)]

    for d in data:
        content.append(
            Paragraph(f"{d.control_id} - {d.status} ({d.risk})", styles["Normal"])
        )

    doc.build(content)

    return FileResponse(path)


@app.on_event("startup")
def create_default_admin():
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        from auth.security import hash_password
        admin = User(
            username="admin",
            password=hash_password("admin123"),
            role="ADMIN"
        )
        db.add(admin)
        db.commit()
        print("Default admin created: admin / admin123")
    db.close()