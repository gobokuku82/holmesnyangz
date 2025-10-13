"""
DB Data Verification Script
PostgreSQL과 MongoDB 데이터 확인
"""

import sys
from pathlib import Path

# backend 디렉토리를 Python path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def check_postgresql():
    """PostgreSQL 데이터 확인"""
    print("\n" + "=" * 60)
    print("=== PostgreSQL Connection Test ===")
    print("=" * 60)

    try:
        from app.db.postgre_db import SessionLocal
        from app.models.real_estate import RealEstate, Transaction, Region, PropertyType
        from sqlalchemy import text

        db = SessionLocal()

        try:
            # 1. 연결 확인
            db.execute(text("SELECT 1"))
            print("✅ PostgreSQL 연결 성공")

            # 2. 테이블별 데이터 카운트
            print("\n--- 테이블 데이터 카운트 ---")

            real_estates_count = db.query(RealEstate).count()
            print(f"✅ real_estates: {real_estates_count:,}개")

            transactions_count = db.query(Transaction).count()
            print(f"✅ transactions: {transactions_count:,}개")

            regions_count = db.query(Region).count()
            print(f"✅ regions: {regions_count}개")

            # 3. 샘플 데이터 조회 (real_estates)
            print("\n--- Sample Data (real_estates) ---")
            sample_estates = db.query(RealEstate).join(Region).limit(5).all()

            for i, estate in enumerate(sample_estates, 1):
                print(f"{i}. {estate.name} ({estate.region.name}) - {estate.property_type.value}")

            # 4. 지역별 매물 통계
            print("\n--- 지역별 매물 통계 (Top 5) ---")
            from sqlalchemy import func

            region_stats = db.query(
                Region.name,
                func.count(RealEstate.id).label('count')
            ).join(RealEstate).group_by(Region.name).order_by(
                func.count(RealEstate.id).desc()
            ).limit(5).all()

            for region_name, count in region_stats:
                print(f"  {region_name}: {count}개")

            # 5. 매물 타입별 통계
            print("\n--- 매물 타입별 통계 ---")
            type_stats = db.query(
                RealEstate.property_type,
                func.count(RealEstate.id).label('count')
            ).group_by(RealEstate.property_type).all()

            for property_type, count in type_stats:
                print(f"  {property_type.value}: {count}개")

            # 6. 샘플 거래 데이터
            print("\n--- Sample Data (transactions) ---")
            sample_transactions = db.query(Transaction).join(RealEstate).join(Region).limit(3).all()

            for i, txn in enumerate(sample_transactions, 1):
                print(f"{i}. {txn.real_estate.name if txn.real_estate else 'N/A'} "
                      f"- 매매가: {txn.sale_price:,}만원, 보증금: {txn.deposit:,}만원")

            print("\n✅ PostgreSQL 데이터 확인 완료!")

        finally:
            db.close()

    except ImportError as e:
        print(f"❌ Import 오류: {e}")
        print("   → app.db.postgre_db 또는 app.models.real_estate를 찾을 수 없습니다")
    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        import traceback
        traceback.print_exc()

def check_mongodb():
    """MongoDB 데이터 확인"""
    print("\n" + "=" * 60)
    print("=== MongoDB Connection Test ===")
    print("=" * 60)

    try:
        from app.core.config import settings

        if not settings.MONGODB_URL:
            print("⚠️ MongoDB URL이 설정되지 않았습니다")
            print("   → .env 파일에 MONGODB_URL 확인")
            return

        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

        # MongoDB 연결 (타임아웃 5초)
        client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)

        try:
            # 연결 확인
            client.admin.command('ping')
            print("✅ MongoDB 연결 성공")

            # 데이터베이스 목록
            db_names = client.list_database_names()
            print(f"\n--- 데이터베이스 목록 ---")
            for db_name in db_names:
                if db_name not in ['admin', 'config', 'local']:
                    print(f"  - {db_name}")

            # 기본 DB의 컬렉션 목록
            if db_names:
                # admin, config, local 제외한 첫 번째 DB 선택
                user_dbs = [name for name in db_names if name not in ['admin', 'config', 'local']]

                if user_dbs:
                    db = client[user_dbs[0]]
                    print(f"\n--- 컬렉션 목록 ({user_dbs[0]}) ---")
                    collections = db.list_collection_names()

                    if collections:
                        for collection_name in collections:
                            count = db[collection_name].count_documents({})
                            print(f"  {collection_name}: {count:,}개 문서")
                    else:
                        print("  컬렉션이 없습니다")
                else:
                    print("\n⚠️ 사용자 데이터베이스가 없습니다 (admin/config/local만 존재)")

            print("\n✅ MongoDB 데이터 확인 완료!")

        finally:
            client.close()

    except ImportError:
        print("⚠️ pymongo가 설치되지 않았습니다")
        print("   → pip install pymongo")
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ MongoDB 연결 실패: {e}")
        print("   → MongoDB 서버가 실행 중인지 확인하세요")
    except Exception as e:
        print(f"❌ MongoDB 오류: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 실행"""
    print("\n" + "=" * 60)
    print("    Database Connection & Data Verification Test")
    print("=" * 60)

    # PostgreSQL 확인
    check_postgresql()

    # MongoDB 확인
    check_mongodb()

    print("\n" + "=" * 60)
    print("=== 테스트 완료 ===")
    print("=" * 60)
    print("\n다음 단계:")
    print("  1. PostgreSQL 데이터 OK → MarketDataTool DB 연동 시작")
    print("  2. 문제 있으면 → 데이터 먼저 수정\n")

if __name__ == "__main__":
    main()
