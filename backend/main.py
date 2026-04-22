from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import shutil
import os
import pandas as pd
from datetime import datetime
from typing import List
import json

from database import SessionLocal, engine as db_engine, Base
from models import Control, Evidence, ComplianceStatus, Alert
from compliance_engine import evaluate_control

Base.metadata.create_all(bind=db_engine)

app = FastAPI(title="Compliance Monitoring System", version="2.0")

# CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_controls():
    db = SessionLocal()

    try:
        existing_count = db.query(Control).count()
        if existing_count > 0:
            print(f" Controls already exist ({existing_count} controls)")
            db.close()
            return

        default_controls = [
            ("CTRL-001", "HIPAA", "IT", "Patient data privacy and security controls", 100),
            ("CTRL-002", "PCI-DSS", "IT", "Payment card data security", 50),
            ("CTRL-003", "NIST", "HR", "Security incident logging", 100),
            ("CTRL-004", "HIPAA", "Finance", "Financial data privacy", 100),
            ("CTRL-005", "PCI-DSS", "Operations", "Transaction processing security", 50),
            ("CTRL-006", "NIST", "Risk", "Risk assessment documentation", 100),
        ]

        for control_id, framework, owner, desc, min_records in default_controls:
            control = Control(
                control_id=control_id,
                framework=framework,
                owner=owner,
                description=desc,
                min_records=min_records
            )
            db.add(control)

        db.commit()
        print(f" Seeded {len(default_controls)} controls")

    except Exception as e:
        print(f" Error seeding controls: {e}")
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    print("\n" + "=" * 50)
    print(" Starting Compliance Monitoring System v2.0")
    print("=" * 50)
    seed_controls()
    print(" Startup complete!\n")



@app.get("/")
def root():
    return {
        "message": "Compliance Monitoring API",
        "status": "running",
        # "version": "2.0"
    }


@app.get("/controls")
def get_controls(db: Session = Depends(get_db)):
    return db.query(Control).all()


@app.post("/evidence/{control_id}")
def upload_evidence(control_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):

    control = db.query(Control).filter(Control.control_id == control_id).first()
    if not control:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    # Validate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > 200 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 200MB)")

    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{control_id}_{timestamp}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    old_evidence = db.query(Evidence).filter(Evidence.control_id == control_id).all()
    for old in old_evidence:
        if os.path.exists(old.file_path):
            os.remove(old.file_path)
        db.delete(old)

    # Save new evidence
    evidence = Evidence(
        control_id=control_id,
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size,
        file_type=file_ext
    )
    db.add(evidence)
    db.commit()

    return {
        "message": "Evidence uploaded successfully",
        "control_id": control_id,
        "file": file.filename,
        "size": file_size
    }


@app.post("/evidence/batch")
def upload_batch_evidence(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):

    results = []

    for file in files:
        file_name = file.filename
        file_ext = os.path.splitext(file_name)[1]

        control_id = None
        for control in db.query(Control).all():
            if control.control_id.lower() in file_name.lower():
                control_id = control.control_id
                break

        if not control_id:
            control_id = f"FILE_{len(results) + 1}"

        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{control_id}_{timestamp}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        control = db.query(Control).filter(Control.control_id == control_id).first()
        if not control:
            control = Control(
                control_id=control_id,
                framework="GENERIC",
                owner="Unknown",
                description=f"Auto-created from file: {file_name}"
            )
            db.add(control)
            db.commit()

        evidence = Evidence(
            control_id=control_id,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            file_type=file_ext
        )
        db.add(evidence)
        db.commit()

        results.append({
            "control_id": control_id,
            "file_name": file_name,
            "size": file_size,
            "status": "uploaded"
        })

    return {"message": f"Uploaded {len(results)} files", "files": results}


@app.post("/evaluate-all")
def evaluate_all_controls(db: Session = Depends(get_db)):

    db.query(ComplianceStatus).delete()
    db.query(Alert).delete()
    db.commit()

    controls = db.query(Control).all()
    results = []

    for control in controls:
        evidence = db.query(Evidence).filter(
            Evidence.control_id == control.control_id
        ).first()

        status, reason, details = evaluate_control_with_details(control, evidence)

        compliance_record = ComplianceStatus(
            control_id=control.control_id,
            status=status,
            reason=reason,
            details=json.dumps(details) if details else None
        )
        db.add(compliance_record)

        if status == "FAILED":
            alert = Alert(
                control_id=control.control_id,
                message=f"{control.control_id}: {reason[:200]}",
                severity="CRITICAL"
            )
            db.add(alert)

        results.append({
            "control": control.control_id,
            "framework": control.framework,
            "owner": control.owner,
            "status": status,
            "reason": reason,
            "details": details
        })

    db.commit()

    compliant = len([r for r in results if r["status"] == "COMPLIANT"])
    failed = len([r for r in results if r["status"] == "FAILED"])

    return {
        "total": len(results),
        "compliant": compliant,
        "failed": failed,
        "compliance_score": round((compliant / len(results)) * 100, 2) if results else 0,
        "results": results
    }


def evaluate_control_with_details(control, evidence):

    if evidence is None:
        return "FAILED", f"No file uploaded for {control.control_id}", {}

    if not os.path.exists(evidence.file_path):
        return "FAILED", f"File not found: {evidence.file_path}", {}

    # Use the compliance engine to validate the file
    from compliance_engine import engine
    return engine.evaluate_file(control, evidence)


@app.post("/evaluate-single/{control_id}")
def evaluate_single_control(control_id: str, db: Session = Depends(get_db)):
    """Evaluate a single control"""

    control = db.query(Control).filter(Control.control_id == control_id).first()
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")

    evidence = db.query(Evidence).filter(Evidence.control_id == control_id).first()
    status, reason, details = evaluate_control_with_details(control, evidence)

    return {
        "control": control.control_id,
        "framework": control.framework,
        "status": status,
        "reason": reason,
        "details": details
    }


@app.get("/compliance-score")
def get_compliance_score(db: Session = Depends(get_db)):
    """Get overall compliance score"""
    statuses = db.query(ComplianceStatus).all()

    if not statuses:
        return {
            "compliance_score": 0,
            "total": 0,
            "compliant": 0,
            "failed": 0
        }

    total = len(statuses)
    compliant = len([s for s in statuses if s.status == "COMPLIANT"])
    failed = len([s for s in statuses if s.status == "FAILED"])
    score = round((compliant / total) * 100, 2) if total > 0 else 0

    return {
        "compliance_score": score,
        "total": total,
        "compliant": compliant,
        "failed": failed
    }


@app.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).order_by(Alert.created_at.desc()).all()


@app.delete("/alerts")
def clear_alerts(db: Session = Depends(get_db)):
    db.query(Alert).delete()
    db.commit()
    return {"message": "All alerts cleared"}


@app.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    controls = db.query(Control).count()
    evidence = db.query(Evidence).count()
    alerts = db.query(Alert).count()

    return {
        "total_controls": controls,
        "evidence_files": evidence,
        "active_alerts": alerts
    }