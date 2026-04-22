import pandas as pd
from database import SessionLocal
from models import Control


def seed_correct_controls():
    db = SessionLocal()

    # Clear existing controls
    db.query(Control).delete()
    db.commit()

    csv_path = "compliance_large_dataset.csv"

    if not os.path.exists(csv_path):
        print(f" CSV file not found: {csv_path}")
        return

    try:
        df = pd.read_csv(csv_path)
        print(f" Loaded {len(df)} records from CSV")

        # Get unique controls from CSV
        unique_controls = df[['Control', 'Framework', 'Department', 'Control Description']].drop_duplicates()
        print(f" Found {len(unique_controls)} unique controls")

        count = 0
        for _, row in unique_controls.head(100).iterrows():
            control_id = str(row['Control']).strip()  # This will be C0001, C0002, etc.
            framework = str(row['Framework']).strip()
            owner = str(row['Department']).strip()
            description = str(row['Control Description'])[:500] if pd.notna(row['Control Description']) else None

            control = Control(
                control_id=control_id,
                framework=framework,
                owner=owner,
                description=description
            )
            db.add(control)
            count += 1

        db.commit()
        print(f" Seeded {count} controls with correct IDs from CSV")

        # Show first few controls
        controls = db.query(Control).limit(5).all()
        print("\n First 5 controls seeded:")
        for c in controls:
            print(f"  {c.control_id} - {c.framework} - {c.owner}")

    except Exception as e:
        print(f" Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import os

    seed_correct_controls()