"""
MongoDB 데이터 Import 스크립트

JSON 및 CSV 파일을 MongoDB에 import하는 범용 스크립트
사용법:
    python scripts/import_mongo_data.py --db bank --collection kb --file data/은행대출/kb_bank.json
    python scripts/import_mongo_data.py --db bank --collection hana --file data/은행대출/hana_bank.csv
    python scripts/import_mongo_data.py --db bank --dir data/은행대출 --auto-mapping
"""

import argparse
import json
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 파일명에서 컬렉션 이름 자동 매핑
FILE_TO_COLLECTION_MAPPING = {
    'kb_bank': 'kb',
    'kbank': 'k',
    'hana_bank': 'hana',
    'kakao_bank': 'kakao',
    'shinhan': 'sinhan',
    'woori_bank': 'woori',
    'sc제일은행': 'sc',
    'sc_bank': 'sc',
}


def read_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """JSON 파일 읽기"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 데이터가 리스트가 아니면 리스트로 감싸기
            if not isinstance(data, list):
                data = [data]
            logger.info(f"JSON 파일 읽기 성공: {file_path} ({len(data)} 건)")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {file_path} - {e}")
        raise
    except Exception as e:
        logger.error(f"파일 읽기 오류: {file_path} - {e}")
        raise


def read_csv_file(file_path: Path) -> List[Dict[str, Any]]:
    """CSV 파일 읽기"""
    try:
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        logger.info(f"CSV 파일 읽기 성공: {file_path} ({len(data)} 건)")
        return data
    except Exception as e:
        logger.error(f"CSV 파일 읽기 오류: {file_path} - {e}")
        raise


def get_collection_name_from_filename(filename: str) -> Optional[str]:
    """파일명에서 컬렉션 이름 추출"""
    name_without_ext = Path(filename).stem

    # 정확히 매칭되는 것 먼저 확인
    if name_without_ext in FILE_TO_COLLECTION_MAPPING:
        return FILE_TO_COLLECTION_MAPPING[name_without_ext]

    # 부분 매칭 확인
    for key, collection in FILE_TO_COLLECTION_MAPPING.items():
        if key in name_without_ext.lower():
            return collection

    return None


def import_to_mongodb(
    db_name: str,
    collection_name: str,
    data: List[Dict[str, Any]],
    mongodb_url: Optional[str] = None,
    clear_existing: bool = False
) -> int:
    """MongoDB에 데이터 import"""
    try:
        # MongoDB 연결 (함수형 인터페이스 사용)
        from app.db.mongo_db import get_collection as get_mongo_collection

        collection = get_mongo_collection(db_name, collection_name, mongodb_url)

        # 기존 데이터 삭제 옵션
        if clear_existing:
            deleted_count = collection.delete_many({}).deleted_count
            logger.info(f"기존 데이터 삭제: {deleted_count} 건")

        # 데이터 삽입
        if data:
            try:
                result = collection.insert_many(data, ordered=False)
                inserted_count = len(result.inserted_ids)
                logger.info(f"데이터 삽입 성공: {inserted_count} 건")
                return inserted_count
            except BulkWriteError as e:
                # 중복 키 오류 등 일부 실패해도 계속 진행
                inserted_count = e.details.get('nInserted', 0)
                logger.warning(f"일부 데이터 삽입 실패 (중복 가능): {len(e.details.get('writeErrors', []))} 건")
                logger.info(f"성공적으로 삽입된 데이터: {inserted_count} 건")
                return inserted_count
        else:
            logger.warning("삽입할 데이터가 없습니다")
            return 0

    except Exception as e:
        logger.error(f"MongoDB import 오류: {e}")
        raise


def import_file(
    file_path: Path,
    db_name: str,
    collection_name: Optional[str] = None,
    mongodb_url: Optional[str] = None,
    clear_existing: bool = False
) -> int:
    """단일 파일 import"""
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    # 컬렉션 이름이 지정되지 않은 경우 파일명에서 추출
    if not collection_name:
        collection_name = get_collection_name_from_filename(file_path.name)
        if not collection_name:
            raise ValueError(
                f"컬렉션 이름을 자동으로 추출할 수 없습니다: {file_path.name}\n"
                "--collection 옵션을 사용하여 직접 지정해주세요."
            )
        logger.info(f"자동 매핑된 컬렉션: {collection_name}")

    # 파일 확장자에 따라 읽기 방식 선택
    suffix = file_path.suffix.lower()
    if suffix == '.json':
        data = read_json_file(file_path)
    elif suffix == '.csv':
        data = read_csv_file(file_path)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {suffix} (JSON 또는 CSV만 가능)")

    # MongoDB에 import
    return import_to_mongodb(db_name, collection_name, data, mongodb_url, clear_existing)


def import_directory(
    dir_path: Path,
    db_name: str,
    mongodb_url: Optional[str] = None,
    clear_existing: bool = False
) -> Dict[str, int]:
    """디렉토리 내 모든 JSON/CSV 파일 import (자동 매핑)"""
    if not dir_path.exists() or not dir_path.is_dir():
        raise NotADirectoryError(f"디렉토리를 찾을 수 없습니다: {dir_path}")

    results = {}
    files = list(dir_path.glob('*.json')) + list(dir_path.glob('*.csv'))

    if not files:
        logger.warning(f"디렉토리에 JSON/CSV 파일이 없습니다: {dir_path}")
        return results

    logger.info(f"총 {len(files)} 개 파일 발견")

    for file_path in files:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"파일 처리 중: {file_path.name}")
            logger.info(f"{'='*60}")

            count = import_file(
                file_path=file_path,
                db_name=db_name,
                collection_name=None,  # 자동 매핑
                mongodb_url=mongodb_url,
                clear_existing=clear_existing
            )
            results[file_path.name] = count

        except Exception as e:
            logger.error(f"파일 처리 실패: {file_path.name} - {e}")
            results[file_path.name] = 0

    return results


def main():
    parser = argparse.ArgumentParser(
        description='MongoDB 데이터 Import 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 단일 파일 import (컬렉션 이름 직접 지정)
  python scripts/import_mongo_data.py --db bank --collection kb --file backend/data/은행대출/kb_bank.json

  # 단일 파일 import (컬렉션 이름 자동 매핑)
  python scripts/import_mongo_data.py --db bank --file backend/data/은행대출/kb_bank.json

  # 디렉토리 전체 import (자동 매핑)
  python scripts/import_mongo_data.py --db bank --dir backend/data/은행대출 --auto-mapping

  # 기존 데이터 삭제 후 import
  python scripts/import_mongo_data.py --db bank --dir backend/data/은행대출 --auto-mapping --clear
        """
    )

    parser.add_argument('--db', required=True, help='데이터베이스 이름')
    parser.add_argument('--collection', help='컬렉션 이름 (--file 사용 시 선택사항, 미지정시 자동 매핑)')
    parser.add_argument('--file', type=Path, help='Import할 파일 경로 (JSON 또는 CSV)')
    parser.add_argument('--dir', type=Path, help='Import할 디렉토리 경로 (모든 JSON/CSV 파일)')
    parser.add_argument('--auto-mapping', action='store_true', help='디렉토리 import 시 파일명 기반 자동 매핑')
    parser.add_argument('--mongodb-url', help='MongoDB 연결 URL (기본값: .env 설정 또는 localhost)')
    parser.add_argument('--clear', action='store_true', help='import 전 기존 데이터 삭제')

    args = parser.parse_args()

    # 파일 또는 디렉토리 중 하나는 필수
    if not args.file and not args.dir:
        parser.error('--file 또는 --dir 중 하나는 필수입니다')

    if args.file and args.dir:
        parser.error('--file과 --dir은 동시에 사용할 수 없습니다')

    try:
        # 단일 파일 import
        if args.file:
            logger.info("=" * 60)
            logger.info("단일 파일 Import 모드")
            logger.info("=" * 60)

            count = import_file(
                file_path=args.file,
                db_name=args.db,
                collection_name=args.collection,
                mongodb_url=args.mongodb_url,
                clear_existing=args.clear
            )

            logger.info("\n" + "=" * 60)
            logger.info(f"✅ Import 완료: {count} 건")
            logger.info("=" * 60)

        # 디렉토리 import
        elif args.dir:
            if not args.auto_mapping:
                parser.error('디렉토리 import 시 --auto-mapping 옵션이 필요합니다')

            logger.info("=" * 60)
            logger.info("디렉토리 자동 매핑 Import 모드")
            logger.info("=" * 60)

            results = import_directory(
                dir_path=args.dir,
                db_name=args.db,
                mongodb_url=args.mongodb_url,
                clear_existing=args.clear
            )

            # 결과 출력
            logger.info("\n" + "=" * 60)
            logger.info("📊 Import 결과 요약")
            logger.info("=" * 60)

            total = 0
            for filename, count in results.items():
                status = "✅" if count > 0 else "❌"
                logger.info(f"{status} {filename}: {count} 건")
                total += count

            logger.info("=" * 60)
            logger.info(f"총 {total} 건 import 완료")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n❌ Import 실패: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
