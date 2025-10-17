"""
부동산 테이블만 초기화 (채팅 데이터 보존)
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.postgre_db import engine, SessionLocal
from app.models.real_estate import Region, RealEstate, Transaction, NearbyFacility, RealEstateAgent
from app.models.users import UserFavorite
from app.models.trust import TrustScore


def drop_estate_tables():
    """부동산 관련 테이블만 삭제 (채팅 테이블 보존)"""
    print("\n🗑️  부동산 테이블 삭제 중...")

    estate_tables = [
        'trust_scores',
        'nearby_facilities',
        'real_estate_agents',
        'user_favorites',
        'transactions',
        'real_estates',
        'regions'
    ]

    with engine.connect() as conn:
        for table in estate_tables:
            try:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                conn.commit()
                print(f"   ✓ {table}")
            except Exception as e:
                print(f"   ✗ {table}: {e}")

    print("✅ 부동산 테이블 삭제 완료")


def create_estate_tables():
    """부동산 관련 테이블만 생성"""
    print("\n📦 부동산 테이블 생성 중...")

    # Base.metadata에서 부동산 관련 테이블만 선택
    from app.db.postgre_db import Base

    # 부동산 관련 테이블들의 metadata
    tables_to_create = [
        Region.__table__,
        RealEstate.__table__,
        Transaction.__table__,
        NearbyFacility.__table__,
        RealEstateAgent.__table__,
        TrustScore.__table__,
        UserFavorite.__table__
    ]

    for table in tables_to_create:
        table.create(bind=engine, checkfirst=True)
        print(f"   ✓ {table.name}")

    print("✅ 부동산 테이블 생성 완료\n")

    print("생성된 테이블:")
    for table in tables_to_create:
        print(f"  - {table.name}")


def init_estate_only(drop_existing=True):
    """
    부동산 테이블만 초기화 (채팅 데이터 보존)

    Args:
        drop_existing: True면 기존 부동산 테이블 삭제 후 재생성
    """
    print("=" * 60)
    print("🏢 부동산 테이블 초기화 (채팅 데이터 보존)")
    print("=" * 60)

    if drop_existing:
        drop_estate_tables()

    create_estate_tables()

    print("\n" + "=" * 60)
    print("✅ 부동산 테이블 초기화 완료!")
    print("=" * 60)
    print("\n📝 다음 단계:")
    print("   1. 아파트/오피스텔: uv run python scripts/import_apt_ofst.py")
    print("   2. 원룸: uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom")
    print("   3. 빌라: uv run python scripts/import_villa_house_oneroom.py --auto --type villa")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='부동산 테이블만 초기화')
    parser.add_argument('--no-drop', action='store_true',
                        help='기존 테이블을 삭제하지 않고 생성만 시도')
    args = parser.parse_args()

    init_estate_only(drop_existing=not args.no_drop)
