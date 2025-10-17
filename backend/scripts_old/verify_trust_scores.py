"""Quick verification script for TrustScore data"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.postgre_db import SessionLocal
from app.models.trust import TrustScore

session = SessionLocal()

print("Sample TrustScore Records:")
print("="*100)

samples = session.query(TrustScore).limit(5).all()
for ts in samples:
    print(f"ID: {ts.id} | RealEstate ID: {ts.real_estate_id} | Score: {float(ts.score):.2f}")
    print(f"Notes: {ts.verification_notes}")
    print(f"Calculated At: {ts.calculated_at}")
    print("-"*100)

session.close()
