from fastapi import FastAPI, UploadFile, File
from sqlalchemy.orm import Session
import shutil
import os

from database import SessionLocal, engine
from models import Base, Control, Evidence, ComplianceStatus, Alert
from compliance_engine import evaluate_control

Base.metadata.create_all(bind=engine)

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================
# CREATE CONTROL
# ============================
@app.post("/controls")
def create_control(control_id: str, framework: str, owner: str):
    db = SessionLocal()

    control = Control(
        control_id=control_id,
        framework=framework,
        owner=owner
    )
    db.add(control)
    db.commit()
    return {"message": "Control created"}


# ============================
# GET CONTROLS
# ============================
@app.get("/controls")
def get_controls():
    db = SessionLocal()
    controls = db.query(Control).all()
    return controls


# ============================
# UPLOAD EVIDENCE
# ============================
@app.post("/evidence/{control_id}")
def upload_evidence(control_id: str, file: UploadFile = File(...)):
    db = SessionLocal()

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    evidence = Evidence(control_id=control_id, file_path=file_path)
    db.add(evidence)
    db.commit()

    return {"message": "Evidence uploaded", "file": file.filename}


# ============================
# RUN COMPLIANCE ENGINE
# ============================
@app.get("/evaluate")
def run_evaluation():
    db = SessionLocal()

    controls = db.query(Control).all()

    results = []

    for control in controls:
        evidence = db.query(Evidence).filter(Evidence.control_id == control.control_id).first()

        status = evaluate_control(control, evidence)

        db.add(ComplianceStatus(control_id=control.control_id, status=status))

        if status == "FAILED":
            db.add(Alert(message=f"{control.control_id} failed", severity="CRITICAL"))

        results.append({
            "control": control.control_id,
            "status": status
        })

    db.commit()
    return results


# ============================
# GET ALERTS
# ============================
@app.get("/alerts")
def get_alerts():
    db = SessionLocal()
    return db.query(Alert).all()


@app.delete("/alerts")
def clear_alerts():
    db = SessionLocal()

    db.query(Alert).delete()
    db.commit()

    return {"message": "All alerts cleared"}