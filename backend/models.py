from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.sql import func
from database import Base


class Control(Base):
    __tablename__ = "controls"

    id = Column(Integer, primary_key=True, index=True)
    control_id = Column(String, unique=True, index=True, nullable=False)
    framework = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    description = Column(String, nullable=True)
    required_fields = Column(String, nullable=True)
    min_records = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    control_id = Column(String, index=True, nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    file_type = Column(String, nullable=True)
    record_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class ComplianceStatus(Base):
    __tablename__ = "compliance_status"

    id = Column(Integer, primary_key=True, index=True)
    control_id = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False)
    risk = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    control_id = Column(String, index=True, nullable=True)
    message = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Integer, default=0)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String, nullable=True)


