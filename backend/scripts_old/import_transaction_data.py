"""
CSV 데이터에서 거래 가격 정보를 Transaction 테이블로 가져오는 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.postgre_db import SessionLocal
from app.models.real_estate import RealEstate, Transaction, TransactionType, Region


def import_transaction_data(csv_path: str):
    """
    CSV 파일에서 거래 가격 정보를 Transaction 테이블로 가져오기

    CSV에는 다음 가격 정보가 있습니다:
    - 매매_최저가, 매매_최고가
    - 전세_최저가, 전세_최고가
    - 월세_최저가, 월세_최고가
    - 최소전용, 최대전용 (면적)

    각 단지에 대해 가격 범위 정보를 Transaction으로 저장합니다.
    """

    # CSV 읽기
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"총 {len(df)}개의 레코드 발견")

    # 데이터베이스 연결
    db = SessionLocal()

    try:
        sucess_count = 0
        error_count = 0

        # 현재 날짜를 거래일로 사용 (실제 거래일 정보가 없으므로)
        current_date = datetime.now()

        for idx, row in df.iterrows():
            try:
          
                real_estate = db.query(RealEstate).filter(
                    RealEstate.code == str(row['단지코드'])
                ).first()
                # 지역 정보
                
                region = real_estate.region

                # 매매 거래 정보
                if pd.notna(row['매매_최저가']) and row['매매_최저가'] > 0:
                    sale = Transaction(
                        real_estate_id=real_estate.id,
                        region_id=region.id,
                        transaction_type=TransactionType.SALE,
                        transaction_date=current_date,
                        min_sale_price=int(row['매매_최저가']),
                        max_sale_price=int(row['매매_최고가']) if pd.notna(row['매매_최고가']) else int(row['매매_최저가']),
                    )
                    db.add(sale)
                    sucess_count += 1

                # 전세 거래 정보
                if pd.notna(row['전세_최저가']) and row['전세_최저가'] > 0:
                    jeonse = Transaction(
                        real_estate_id=real_estate.id,
                        region_id=region.id,
                        transaction_type=TransactionType.JEONSE,
                        transaction_date=current_date,
                        min_deposit=int(row['전세_최저가']),
                        max_deposit=int(row['전세_최고가']) if pd.notna(row['전세_최고가']) else int(row['전세_최저가']),
                    )
                    db.add(jeonse)
                    sucess_count += 1

                # 월세 거래 정보
                if pd.notna(row['월세_최저가']) and row['월세_최저가'] > 0:
                    rent = Transaction(
                        real_estate_id=real_estate.id,
                        region_id=region.id,
                        transaction_type=TransactionType.RENT,
                        transaction_date=current_date,
                        min_monthly_rent=int(row['월세_최저가']),
                        max_monthly_rent=int(row['월세_최고가']) if pd.notna(row['월세_최고가']) else int(row['월세_최저가']),
                    )
                    db.add(rent)
                    sucess_count += 1
            
            except Exception as e:
                print(f"레코드 처리 중 오류: {e}")
                error_count += 1
                continue

        # 커밋
        db.commit()
        print(f"완료: 성공 {sucess_count}개, 실패 {error_count}개")
        
    except Exception as e:
        print(f"데이터베이스 오류: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    csv_file = Path("/Users/macbook/Desktop/learn/side_project/frontend/public/data/real_estate_with_coordinates_kakao.csv")

    if not csv_file.exists():
        print(f"❌ CSV 파일을 찾을 수 없습니다: {csv_file}")
        sys.exit(1)

    print("=" * 60)
    print("💰 거래 가격 데이터 Import")
    print("=" * 60)
    print(f"\n📂 파일: {csv_file.name}")

    import_transaction_data(str(csv_file))

    print("\n✅ Import 완료!")