"""
Check Config paths for legal search
"""

import sys
from pathlib import Path

# Add service directory to path
service_dir = Path(__file__).parent / "backend" / "app" / "service"
sys.path.insert(0, str(service_dir))

from core.config import Config

print("=" * 80)
print("Legal Search Configuration Check")
print("=" * 80)

print("\n[BASE PATHS]")
print(f"  BASE_DIR: {Config.BASE_DIR}")
print(f"  LEGAL_INFO_BASE: {Config.LEGAL_INFO_BASE}")

print("\n[LEGAL_PATHS]")
for key, path in Config.LEGAL_PATHS.items():
    exists = "✓" if Path(path).exists() else "✗"
    print(f"  {exists} {key}: {path}")

print("\n[EMBEDDING MODEL CHECK]")
model_path = Config.LEGAL_PATHS["embedding_model"]
print(f"  Path: {model_path}")
print(f"  Exists: {Path(model_path).exists()}")

if Path(model_path).exists():
    print(f"  Contents:")
    for item in Path(model_path).iterdir():
        print(f"    - {item.name}")

print("\n[CHROMADB CHECK]")
chroma_path = Config.LEGAL_PATHS["chroma_db"]
print(f"  Path: {chroma_path}")
print(f"  Exists: {Path(chroma_path).exists()}")

if Path(chroma_path).exists():
    print(f"  Contents:")
    for item in Path(chroma_path).iterdir():
        print(f"    - {item.name}")

print("\n[SQLITE CHECK]")
sqlite_path = Config.LEGAL_PATHS["sqlite_db"]
print(f"  Path: {sqlite_path}")
print(f"  Exists: {Path(sqlite_path).exists()}")

if Path(sqlite_path).exists():
    import sqlite3
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # Get table list
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"  Tables: {[t[0] for t in tables]}")

    # Get law count
    cursor.execute("SELECT COUNT(*) FROM laws")
    law_count = cursor.fetchone()[0]
    print(f"  Total laws: {law_count}")

    # Get article count
    cursor.execute("SELECT COUNT(*) FROM articles")
    article_count = cursor.fetchone()[0]
    print(f"  Total articles: {article_count}")

    conn.close()

print("\n" + "=" * 80)
print("Configuration check completed!")
print("=" * 80)
