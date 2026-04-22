import os
import pandas as pd
import json
from datetime import datetime


class ComplianceEngine:
    def __init__(self):
        self.validation_rules = {
            "HIPAA": {
                "required_columns": ["patient_id", "record_date", "access_type", "user_id"],
                "min_records": 100,
                "keywords": ["phi", "protected health", "consent", "authorization", "privacy"]
            },
            "PCI-DSS": {
                "required_columns": ["transaction_id", "amount", "card_last4", "timestamp"],
                "min_records": 50,
                "keywords": ["payment", "cardholder", "encryption", "tokenization", "pci"]
            },
            "NIST": {
                "required_columns": ["event_id", "timestamp", "event_type", "source_ip"],
                "min_records": 100,
                "keywords": ["security", "control", "risk", "assessment", "nist"]
            }
        }

    def evaluate_file(self, control, evidence):
        """
        Evaluate a single file against control requirements
        Returns (status, reason, details)
        """
        if evidence is None:
            return "FAILED", "No file uploaded", {}

        if not os.path.exists(evidence.file_path):
            return "FAILED", "File not found on server", {}

        # Get file extension
        file_ext = os.path.splitext(evidence.file_path)[1].lower()

        if file_ext == '.csv':
            return self._validate_csv(control, evidence)
        elif file_ext in ['.xlsx', '.xls']:
            return self._validate_excel(control, evidence)
        elif file_ext == '.json':
            return self._validate_json(control, evidence)
        elif file_ext == '.pdf':
            return self._validate_pdf(control, evidence)
        elif file_ext == '.txt':
            return self._validate_text(control, evidence)
        else:
            return self._validate_generic(control, evidence)

    def _validate_csv(self, control, evidence):
        try:
            df = pd.read_csv(evidence.file_path)
            return self._validate_dataframe(control, evidence, df)
        except Exception as e:
            return "FAILED", f"Error reading CSV: {str(e)}", {"error": str(e)}

    def _validate_excel(self, control, evidence):
        try:
            df = pd.read_excel(evidence.file_path)
            return self._validate_dataframe(control, evidence, df)
        except Exception as e:
            return "FAILED", f"Error reading Excel: {str(e)}", {"error": str(e)}

    def _validate_json(self, control, evidence):
        try:
            with open(evidence.file_path, 'r') as f:
                data = json.load(f)

            # Convert to DataFrame if it's a list of records
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict) and 'records' in data:
                df = pd.DataFrame(data['records'])
            else:
                return "FAILED", "JSON format not recognized. Expected array or {records: []}", {}

            return self._validate_dataframe(control, evidence, df)
        except Exception as e:
            return "FAILED", f"Error reading JSON: {str(e)}", {"error": str(e)}

    def _validate_pdf(self, control, evidence):
        try:
            file_size = os.path.getsize(evidence.file_path)

            if file_size < 10240:  # Less than 10KB
                return "FAILED", f"PDF file too small ({file_size} bytes). Need at least 10KB", {"file_size": file_size}

            try:
                import PyPDF2
                with open(evidence.file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    num_pages = len(pdf_reader.pages)

                    if num_pages == 0:
                        return "FAILED", "PDF has no pages", {"pages": 0}

                    text = ""
                    for i in range(min(3, num_pages)):
                        text += pdf_reader.pages[i].extract_text()

                    rules = self.validation_rules.get(control.framework, {})
                    keywords = rules.get("keywords", [])

                    if keywords:
                        found_keywords = [kw for kw in keywords if kw.lower() in text.lower()]
                        if len(found_keywords) < len(keywords) * 0.5:
                            return "FAILED", f"Missing required keywords. Found {len(found_keywords)}/{len(keywords)}", {
                                "found_keywords": found_keywords, "required_keywords": keywords}

                    return "COMPLIANT", f"PDF validated: {num_pages} pages, {file_size} bytes", {"pages": num_pages,
                                                                                                 "file_size": file_size}
            except ImportError:
                return "COMPLIANT", f"PDF file validated (basic): {file_size} bytes", {"file_size": file_size,
                                                                                       "warning": "Install PyPDF2 for deeper validation"}

        except Exception as e:
            return "FAILED", f"Error validating PDF: {str(e)}", {"error": str(e)}

    def _validate_text(self, control, evidence):
        try:
            with open(evidence.file_path, 'r') as f:
                lines = f.readlines()

            record_count = len(lines)
            file_size = os.path.getsize(evidence.file_path)

            rules = self.validation_rules.get(control.framework, {})
            min_records = rules.get("min_records", control.min_records or 100)

            if record_count < min_records:
                return "FAILED", f"Only {record_count} lines found. Need at least {min_records}", {
                    "record_count": record_count, "min_required": min_records}

            import re
            timestamp_pattern = r'\d{4}-\d{2}-\d{2}'
            has_timestamps = any(re.search(timestamp_pattern, line) for line in lines[:10])

            if control.framework == "NIST" and not has_timestamps:
                return "FAILED", "Missing timestamps in log file", {"has_timestamps": False}

            return "COMPLIANT", f"Text file validated: {record_count} lines, {file_size} bytes", {
                "record_count": record_count, "file_size": file_size}

        except Exception as e:
            return "FAILED", f"Error reading text file: {str(e)}", {"error": str(e)}

    def _validate_dataframe(self, control, evidence, df):
        record_count = len(df)
        file_size = os.path.getsize(evidence.file_path)

        rules = self.validation_rules.get(control.framework, {})
        required_columns = rules.get("required_columns", [])
        min_records = rules.get("min_records", control.min_records or 100)

        details = {
            "record_count": record_count,
            "file_size": file_size,
            "columns": df.columns.tolist(),
            "min_records_required": min_records
        }

        if record_count < min_records:
            return "FAILED", f"Only {record_count} records found. Need at least {min_records}", details

        if required_columns:
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return "FAILED", f"Missing required columns: {missing_columns}", {**details,
                                                                                  "missing_columns": missing_columns,
                                                                                  "required_columns": required_columns}

        if required_columns:
            for col in required_columns:
                if col in df.columns and df[col].isnull().any():
                    null_count = df[col].isnull().sum()
                    if null_count > record_count * 0.1:  # More than 10% nulls
                        return "FAILED", f"Column '{col}' has {null_count} null values ({null_count / record_count * 100:.1f}%)", {
                            **details, "null_counts": {col: null_count}}

        if control.framework == "PCI-DSS" and 'amount' in df.columns:
            if df['amount'].dtype in ['float64', 'int64']:
                negative_count = (df['amount'] < 0).sum()
                if negative_count > 0:
                    return "FAILED", f"Found {negative_count} negative transaction amounts", {**details,
                                                                                              "negative_amounts": negative_count}

        if control.framework == "HIPAA" and 'patient_id' in df.columns:
            duplicates = df['patient_id'].duplicated().sum()
            if duplicates > record_count * 0.05:  # More than 5% duplicates
                return "FAILED", f"Too many duplicate patient IDs: {duplicates}", {**details,
                                                                                   "duplicate_count": duplicates}

        return "COMPLIANT", f"File validated: {record_count} records, {file_size} bytes", details

    def _validate_generic(self, control, evidence):
        """Generic validation for unknown file types"""
        file_size = os.path.getsize(evidence.file_path)

        if file_size == 0:
            return "FAILED", "File is empty", {"file_size": 0}

        if file_size < 1024:  # Less than 1KB
            return "FAILED", f"File too small ({file_size} bytes). Need at least 1KB", {"file_size": file_size}

        return "COMPLIANT", f"Basic validation passed: {file_size} bytes", {"file_size": file_size}


engine = ComplianceEngine()


def evaluate_control(control, evidence):
    status, reason, details = engine.evaluate_file(control, evidence)
    return status