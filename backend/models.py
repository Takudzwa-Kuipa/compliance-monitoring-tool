from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from datetime import datetime
from database import Base

class Control(Base):
    __tablename__ = "controls"

    control_id = Column(String, primary_key=True, index=True)
    framework = Column(String)
    description = Column(String)
    owner = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    control_id = Column(String, ForeignKey("controls.control_id"))
    file_path = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class ComplianceStatus(Base):
    __tablename__ = "compliance_status"

    id = Column(Integer, primary_key=True, index=True)
    control_id = Column(String)
    status = Column(String)
    evaluated_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)
    severity = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)