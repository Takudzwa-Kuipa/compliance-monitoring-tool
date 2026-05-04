import os
import pandas as pd
from database import SessionLocal
from models import Control


FRAMEWORK_RULES = {
    "HIPAA": ["patient_id", "record_date", "access_type", "user_id"],
    "PCI-DSS": ["transaction_id", "amount", "card_last4", "timestamp"],
    "NIST": ["event_id", "timestamp", "event_type", "source_ip"]
}


def seed_correct_controls():
    db = SessionLocal()

    try:
        db.query(Control).delete()
        db.commit()

        csv_path = "compliance_large_dataset.csv"

        if not os.path.exists(csv_path):
            print(f"❌ CSV file not found: {csv_path}")
            return

        df = pd.read_csv(csv_path)
        print(f"✅ Loaded {len(df)} records")

        unique_controls = df[['Control', 'Framework', 'Department', 'Control Description']].drop_duplicates()

        count = 0

        for _, row in unique_controls.head(100).iterrows():
            control_id = str(row['Control']).strip()
            framework = str(row['Framework']).strip()
            owner = str(row['Department']).strip()
            description = str(row['Control Description'])[:500] if pd.notna(row['Control Description']) else None

            required_fields = FRAMEWORK_RULES.get(framework, [])

            control = Control(
                control_id=control_id,
                framework=framework,
                owner=owner,
                description=description,
                required_fields=",".join(required_fields),
                min_records=100
            )

            db.add(control)
            count += 1

        db.commit()

        print(f"✅ Seeded {count} controls")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    seed_correct_controls()