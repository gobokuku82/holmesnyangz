"""
MongoDB 대출 데이터 스키마 확인 스크립트

사용법:
    python scripts/check_mongo_schema.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.mongo_db import mongodb
import json


def check_bank_collections():
    """은행 컬렉션 확인 및 샘플 데이터 출력"""
    print("=" * 80)
    print("MongoDB 대출 데이터 스키마 확인")
    print("=" * 80)

    bank_db = mongodb.get_database("bank")
    collections = bank_db.list_collection_names()

    print(f"\n총 컬렉션 수: {len(collections)}")
    print(f"컬렉션 목록: {', '.join(collections)}\n")

    for collection_name in collections:
        print("=" * 80)
        print(f"컬렉션: {collection_name}")
        print("=" * 80)

        collection = bank_db[collection_name]

        # 통계
        count = collection.count_documents({})
        print(f"총 문서 수: {count}")

        if count > 0:
            # 샘플 문서 1개 조회
            sample = collection.find_one()

            if sample:
                # _id 제거 (ObjectId는 JSON 직렬화 불가)
                if '_id' in sample:
                    sample['_id'] = str(sample['_id'])

                print(f"\n샘플 문서:")
                print(json.dumps(sample, ensure_ascii=False, indent=2))

                print(f"\n필드 목록:")
                for key in sample.keys():
                    value_type = type(sample[key]).__name__
                    print(f"  - {key}: {value_type}")
        else:
            print("  ⚠️ 데이터가 없습니다")

        print()


if __name__ == '__main__':
    try:
        check_bank_collections()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
