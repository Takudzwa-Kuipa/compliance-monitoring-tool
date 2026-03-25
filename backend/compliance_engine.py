from datetime import datetime

def evaluate_control(control, evidence):
    if not evidence:
        return "FAILED"

    age = (datetime.utcnow() - evidence.uploaded_at).days

    if age > 30:
        return "EXPIRED"

    return "COMPLIANT"