"""
Agent Tests for Real Estate Chatbot
각 에이전트의 개별 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from backend.agents.analyzer_agent import AnalyzerAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.supervisor_agent import SupervisorAgent
from backend.agents.price_search_agent import PriceSearchAgent
from backend.agents.finance_agent import FinanceAgent
from backend.agents.location_agent import LocationAgent
from backend.agents.legal_agent import LegalAgent


class TestAnalyzerAgent:
    """Analyzer 에이전트 테스트"""
    
    @pytest.fixture
    def agent(self):
        return AnalyzerAgent()
    
    @pytest.mark.asyncio
    async def test_analyze_price_inquiry(self, agent):
        """가격 문의 분석 테스트"""
        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=Mock(
                content='{"intent": "price_inquiry", "entities": {"location": "강남구", "property_type": "아파트"}, "confidence": 0.95}'
            ))
            
            result = await agent.analyze("강남구 아파트 시세가 어떻게 되나요?")
            
            assert result["intent"] == "price_inquiry"
            assert result["entities"]["location"] == "강남구"
            assert result["entities"]["property_type"] == "아파트"
            assert result["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_analyze_loan_consultation(self, agent):
        """대출 상담 분석 테스트"""
        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=Mock(
                content='{"intent": "loan_consultation", "entities": {"loan_amount": 500000000, "property_price": 800000000}, "confidence": 0.90}'
            ))
            
            result = await agent.analyze("8억 아파트 구매 시 5억 대출 가능한가요?")
            
            assert result["intent"] == "loan_consultation"
            assert result["entities"]["loan_amount"] == 500000000
            assert result["confidence"] == 0.90
    
    @pytest.mark.asyncio
    async def test_analyze_location_inquiry(self, agent):
        """입지 문의 분석 테스트"""
        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=Mock(
                content='{"intent": "location_inquiry", "entities": {"location": "판교", "interests": ["교통", "학군"]}, "confidence": 0.88}'
            ))
            
            result = await agent.analyze("판교 지역 교통과 학군은 어떤가요?")
            
            assert result["intent"] == "location_inquiry"
            assert result["entities"]["location"] == "판교"
            assert "교통" in result["entities"]["interests"]
            assert "학군" in result["entities"]["interests"]


class TestPlannerAgent:
    """Planner 에이전트 테스트"""
    
    @pytest.fixture
    def agent(self):
        return PlannerAgent()
    
    @pytest.mark.asyncio
    async def test_plan_single_agent(self, agent):
        """단일 에이전트 계획 테스트"""
        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=Mock(
                content='{"steps": ["가격 조회"], "agents": ["price_search_agent"], "strategy": "sequential"}'
            ))
            
            result = await agent.plan(
                intent="price_inquiry",
                entities={"location": "강남구"}
            )
            
            assert len(result["steps"]) == 1
            assert result["agents"] == ["price_search_agent"]
            assert result["strategy"] == "sequential"
    
    @pytest.mark.asyncio
    async def test_plan_multiple_agents(self, agent):
        """다중 에이전트 계획 테스트"""
        with patch.object(agent, 'llm') as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=Mock(
                content='{"steps": ["가격 조회", "대출 계산", "세금 확인"], "agents": ["price_search_agent", "finance_agent", "legal_agent"], "strategy": "parallel"}'
            ))
            
            result = await agent.plan(
                intent="purchase_consultation",
                entities={"location": "강남구", "budget": 1000000000}
            )
            
            assert len(result["steps"]) == 3
            assert len(result["agents"]) == 3
            assert result["strategy"] == "parallel"


class TestPriceSearchAgent:
    """가격 검색 에이전트 테스트"""
    
    @pytest.fixture
    def agent(self):
        return PriceSearchAgent()
    
    @pytest.mark.asyncio
    async def test_search_real_estate_price(self, agent):
        """부동산 가격 검색 테스트"""
        with patch('backend.tools.price_tools.search_real_estate_price') as mock_tool:
            mock_tool.return_value = {
                "location": "강남구",
                "average_price": 5000000000,
                "price_per_pyeong": 50000000
            }
            
            result = await agent.execute(
                query="강남구 아파트 시세",
                entities={"location": "강남구", "property_type": "아파트"}
            )
            
            assert result["success"] == True
            assert "강남구" in result["content"]
    
    @pytest.mark.asyncio
    async def test_analyze_price_trend(self, agent):
        """가격 추세 분석 테스트"""
        with patch('backend.tools.price_tools.analyze_price_trend') as mock_tool:
            mock_tool.return_value = {
                "trend": "상승",
                "change_rate": 5.2,
                "period": "최근 1년"
            }
            
            result = await agent.execute(
                query="강남구 아파트 가격 추세",
                entities={"location": "강남구", "property_type": "아파트"}
            )
            
            assert result["success"] == True


class TestFinanceAgent:
    """금융 에이전트 테스트"""
    
    @pytest.fixture
    def agent(self):
        return FinanceAgent()
    
    @pytest.mark.asyncio
    async def test_calculate_loan(self, agent):
        """대출 계산 테스트"""
        with patch('backend.tools.finance_tools.calculate_loan_limit') as mock_tool:
            mock_tool.return_value = {
                "max_loan": 500000000,
                "ltv_ratio": 60,
                "dti_ratio": 40
            }
            
            result = await agent.execute(
                query="연소득 1억으로 얼마까지 대출 가능한가요?",
                entities={"annual_income": 100000000}
            )
            
            assert result["success"] == True
    
    @pytest.mark.asyncio
    async def test_calculate_monthly_payment(self, agent):
        """월 상환액 계산 테스트"""
        with patch('backend.tools.finance_tools.simulate_monthly_payment') as mock_tool:
            mock_tool.return_value = {
                "monthly_payment": 2500000,
                "total_interest": 150000000,
                "total_payment": 650000000
            }
            
            result = await agent.execute(
                query="5억 대출 시 월 상환액",
                entities={"loan_amount": 500000000, "interest_rate": 3.5, "years": 30}
            )
            
            assert result["success"] == True


class TestLocationAgent:
    """입지 분석 에이전트 테스트"""
    
    @pytest.fixture
    def agent(self):
        return LocationAgent()
    
    @pytest.mark.asyncio
    async def test_search_nearby_facilities(self, agent):
        """주변 시설 검색 테스트"""
        with patch('backend.tools.location_tools.search_nearby_facilities') as mock_tool:
            mock_tool.return_value = {
                "schools": ["강남초등학교", "대치중학교"],
                "hospitals": ["삼성의료원"],
                "subway": ["강남역", "선릉역"]
            }
            
            result = await agent.execute(
                query="강남구 주변 시설",
                entities={"location": "강남구"}
            )
            
            assert result["success"] == True
    
    @pytest.mark.asyncio
    async def test_evaluate_accessibility(self, agent):
        """접근성 평가 테스트"""
        with patch('backend.tools.location_tools.evaluate_accessibility') as mock_tool:
            mock_tool.return_value = {
                "score": 8.5,
                "subway_distance": "도보 5분",
                "bus_lines": 15
            }
            
            result = await agent.execute(
                query="판교 교통 접근성",
                entities={"location": "판교"}
            )
            
            assert result["success"] == True


class TestLegalAgent:
    """법률 에이전트 테스트"""
    
    @pytest.fixture
    def agent(self):
        return LegalAgent()
    
    @pytest.mark.asyncio
    async def test_explain_contract_terms(self, agent):
        """계약 조건 설명 테스트"""
        with patch('backend.tools.legal_tools.explain_contract_terms') as mock_tool:
            mock_tool.return_value = {
                "key_terms": ["계약금", "중도금", "잔금"],
                "cautions": ["특약사항 확인", "등기부 확인"]
            }
            
            result = await agent.execute(
                query="부동산 계약서 주의사항",
                entities={"contract_type": "매매"}
            )
            
            assert result["success"] == True
    
    @pytest.mark.asyncio
    async def test_calculate_taxes(self, agent):
        """세금 계산 테스트"""
        with patch('backend.tools.legal_tools.calculate_acquisition_tax') as mock_tool:
            mock_tool.return_value = {
                "acquisition_tax": 30000000,
                "registration_tax": 5000000,
                "total_tax": 35000000
            }
            
            result = await agent.execute(
                query="10억 아파트 취득세",
                entities={"property_price": 1000000000}
            )
            
            assert result["success"] == True


class TestSupervisorAgent:
    """Supervisor 에이전트 테스트"""
    
    @pytest.fixture
    def agent(self):
        return SupervisorAgent()
    
    @pytest.mark.asyncio
    async def test_execute_single_agent(self, agent):
        """단일 에이전트 실행 테스트"""
        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value={
            "success": True,
            "content": "Test result"
        })
        
        result = await agent.execute_agent(
            agent=mock_agent,
            query="테스트 쿼리",
            entities={},
            context={}
        )
        
        assert result["success"] == True
        assert result["content"] == "Test result"
        mock_agent.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_retry(self, agent):
        """재시도 로직 테스트"""
        mock_agent = Mock()
        
        # 첫 번째 호출은 실패, 두 번째는 성공
        mock_agent.execute = AsyncMock(side_effect=[
            Exception("Temporary error"),
            {"success": True, "content": "Success after retry"}
        ])
        
        result = await agent.execute_agent(
            agent=mock_agent,
            query="테스트 쿼리",
            entities={},
            context={"max_retries": 2}
        )
        
        assert result["success"] == True
        assert mock_agent.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, agent):
        """병렬 실행 테스트"""
        # Mock 에이전트들 생성
        agents = []
        for i in range(3):
            mock_agent = Mock()
            mock_agent.execute = AsyncMock(return_value={
                "success": True,
                "content": f"Result {i}"
            })
            agents.append(mock_agent)
        
        # 병렬 실행
        tasks = [
            agent.execute_agent(a, "query", {}, {})
            for a in agents
        ]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["success"] == True
            assert result["content"] == f"Result {i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])