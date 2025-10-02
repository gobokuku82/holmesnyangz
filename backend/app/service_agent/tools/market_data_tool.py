"""
Market Data Tool - 부동산 시세 정보 제공
Mock 데이터 기반
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path


logger = logging.getLogger(__name__)


class MarketDataTool:
    """부동산 시세 데이터 Tool"""

    def __init__(self):
        self.mock_data = self._load_mock_data()

    def _load_mock_data(self) -> Dict:
        """Load mock market data"""
        try:
            backend_dir = Path(__file__).parent.parent.parent.parent
            data_path = backend_dir / "data" / "storage" / "real_estate" / "mock_market_data.json"

            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info(f"Market data loaded: {len(data.get('regions', {}))} regions")
            return data

        except Exception as e:
            logger.error(f"Failed to load mock data: {e}")
            return {"regions": {}, "market_analysis": {}}

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Search market data"""
        params = params or {}

        region = params.get('region') or self._extract_region(query)
        property_type = params.get('property_type', 'apartment')

        logger.info(f"Market search - region: {region}, type: {property_type}")

        regions_data = self.mock_data.get('regions', {})
        results = []

        if region and region in regions_data:
            region_data = regions_data[region][property_type]
            results.append({
                "region": region,
                "property_type": property_type,
                **region_data
            })
        else:
            # Return multiple regions
            for region_name, region_data in list(regions_data.items())[:5]:
                if property_type in region_data:
                    results.append({
                        "region": region_name,
                        "property_type": property_type,
                        **region_data[property_type]
                    })

        return {
            "status": "success",
            "data": results,
            "market_analysis": self.mock_data.get('market_analysis', {}),
            "result_count": len(results)
        }

    def _extract_region(self, query: str) -> Optional[str]:
        """Extract region from query"""
        regions = ["강남구", "서초구", "송파구", "마포구", "용산구", "성동구"]
        for region in regions:
            if region in query:
                return region
        return None
