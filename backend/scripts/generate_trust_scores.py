"""
TrustScore Generation Script
Generates trust scores for all properties in the database based on:
1. Transaction count (more transactions = higher trust)
2. Price appropriateness (price within reasonable range for area)
3. Data completeness (more fields filled = higher trust)
4. Agent registration status (registered agent = higher trust)

Usage:
    python backend/scripts/generate_trust_scores.py
"""

import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import func, and_

from app.db.postgre_db import SessionLocal
from app.models.real_estate import RealEstate, Transaction, RealEstateAgent
from app.models.trust import TrustScore


def calculate_transaction_score(real_estate: RealEstate, transactions: list) -> float:
    """
    Calculate score based on transaction count (0-25 points)
    More transactions indicate more market activity and trust
    """
    transaction_count = len(transactions)

    if transaction_count == 0:
        return 0.0
    elif transaction_count == 1:
        return 10.0
    elif transaction_count <= 3:
        return 15.0
    elif transaction_count <= 5:
        return 20.0
    else:
        return 25.0


def calculate_price_appropriateness_score(
    transactions: list,
    avg_price_in_area: float
) -> float:
    """
    Calculate score based on price appropriateness (0-25 points)
    Price within reasonable range for area indicates legitimate listing
    Uses most recent transaction price
    """
    if not transactions or not avg_price_in_area or avg_price_in_area == 0:
        return 10.0  # Neutral score if no comparison data

    # Get most recent transaction price (sale_price, deposit, or monthly_rent)
    recent_transaction = transactions[0]
    price = (
        recent_transaction.sale_price or
        recent_transaction.deposit or
        recent_transaction.monthly_rent or
        0
    )

    if price == 0:
        return 10.0  # Neutral score if no price data

    price = float(price)
    avg_price_in_area = float(avg_price_in_area)
    deviation = abs(price - avg_price_in_area) / avg_price_in_area

    if deviation <= 0.15:  # Within 15% of average
        return 25.0
    elif deviation <= 0.30:  # Within 30% of average
        return 20.0
    elif deviation <= 0.50:  # Within 50% of average
        return 15.0
    elif deviation <= 1.0:  # Within 100% of average
        return 10.0
    else:  # More than 100% deviation
        return 5.0


def calculate_data_completeness_score(real_estate: RealEstate) -> float:
    """
    Calculate score based on data completeness (0-25 points)
    More complete data indicates more trustworthy listing
    """
    fields_to_check = [
        real_estate.name,
        real_estate.address,
        real_estate.latitude,
        real_estate.longitude,
        real_estate.property_type,
        real_estate.total_households,
        real_estate.total_buildings,
        real_estate.completion_date,
        real_estate.representative_area,
        real_estate.floor_area_ratio,
        real_estate.building_description,
        real_estate.exclusive_area,
        real_estate.supply_area,
        real_estate.direction,
    ]

    filled_count = sum(1 for field in fields_to_check if field is not None)
    total_count = len(fields_to_check)

    completeness_ratio = filled_count / total_count
    return completeness_ratio * 25.0


def calculate_agent_registration_score(real_estate: RealEstate, has_agent: bool) -> float:
    """
    Calculate score based on agent registration status (0-25 points)
    Registered agent indicates higher trust
    """
    if has_agent:
        return 25.0
    else:
        return 15.0  # Still give some points for properties without agents


def generate_trust_scores_batch(session, batch_size: int = 100):
    """
    Generate trust scores for all properties in batches
    """
    # Get total count
    total_properties = session.query(func.count(RealEstate.id)).scalar()

    print(f"Total properties to process: {total_properties}")

    # Process in batches
    offset = 0
    processed = 0
    created = 0
    updated = 0
    errors = 0

    while offset < total_properties:
        print(f"\nProcessing batch {offset//batch_size + 1} (offset: {offset})")

        # Fetch batch of properties
        properties = session.query(RealEstate).offset(offset).limit(batch_size).all()

        if not properties:
            break

        for real_estate in properties:
            try:
                # Fetch related data
                # 1. Transactions for this property
                transactions = session.query(Transaction).filter(
                    Transaction.real_estate_id == real_estate.id
                ).all()

                # 2. Average price in the same region with same property type
                # Calculate from recent transactions
                avg_price_query = session.query(
                    func.avg(
                        func.coalesce(Transaction.sale_price, 0) +
                        func.coalesce(Transaction.deposit, 0) +
                        func.coalesce(Transaction.monthly_rent, 0)
                    )
                ).join(RealEstate).filter(
                    and_(
                        RealEstate.region_id == real_estate.region_id,
                        RealEstate.property_type == real_estate.property_type,
                        (Transaction.sale_price > 0) | (Transaction.deposit > 0) | (Transaction.monthly_rent > 0)
                    )
                )
                avg_price_in_area = avg_price_query.scalar() or 0.0

                # 3. Check if property has registered agent
                agent = session.query(RealEstateAgent).filter(
                    RealEstateAgent.real_estate_id == real_estate.id
                ).first()
                has_agent = agent is not None

                # Calculate component scores
                transaction_score = calculate_transaction_score(real_estate, transactions)
                price_score = calculate_price_appropriateness_score(transactions, avg_price_in_area)
                completeness_score = calculate_data_completeness_score(real_estate)
                agent_score = calculate_agent_registration_score(real_estate, has_agent)

                # Calculate total score (0-100)
                total_score = transaction_score + price_score + completeness_score + agent_score

                # Generate verification notes
                notes = (
                    f"거래 이력: {len(transactions)}건 ({transaction_score}점) | "
                    f"가격 적정성: {price_score}점 | "
                    f"정보 완전성: {completeness_score:.1f}점 ({completeness_score/25*100:.0f}%) | "
                    f"중개사 등록: {'있음' if has_agent else '없음'} ({agent_score}점)"
                )

                # Check if trust score already exists
                existing_trust_score = session.query(TrustScore).filter(
                    TrustScore.real_estate_id == real_estate.id
                ).first()

                if existing_trust_score:
                    # Update existing
                    existing_trust_score.score = Decimal(str(round(total_score, 2)))
                    existing_trust_score.verification_notes = notes
                    existing_trust_score.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    # Create new
                    trust_score = TrustScore(
                        real_estate_id=real_estate.id,
                        score=Decimal(str(round(total_score, 2))),
                        verification_notes=notes,
                        calculated_at=datetime.utcnow()
                    )
                    session.add(trust_score)
                    created += 1

                processed += 1

                if processed % 50 == 0:
                    print(f"  Processed: {processed}/{total_properties} | Created: {created} | Updated: {updated} | Errors: {errors}")
                    session.commit()

            except Exception as e:
                print(f"  Error processing property ID {real_estate.id}: {e}")
                errors += 1
                session.rollback()
                continue

        # Commit batch
        session.commit()
        offset += batch_size

    print(f"\n{'='*60}")
    print(f"Generation completed!")
    print(f"Total processed: {processed}")
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Errors: {errors}")
    print(f"{'='*60}")


def main():
    """Main execution function"""
    print("="*60)
    print("TrustScore Generation Script")
    print("="*60)

    # Create session
    session = SessionLocal()
    try:
        generate_trust_scores_batch(session, batch_size=100)
    finally:
        session.close()

    print("\nScript execution completed.")


if __name__ == "__main__":
    main()
