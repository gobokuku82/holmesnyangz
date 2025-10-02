"""
Document Generation Agent

문서 생성을 담당하는 에이전트
- 계약서, 신청서, 통지서 등 다양한 법률 문서 생성
- Document Generation Tool과 연동
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional, Annotated
from datetime import datetime
import json

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import tools_condition

from core.states import DocumentAgentState
from tools.document_generation_tool import DocumentGenerationTool


class DocumentAgent:
    """문서 생성 에이전트"""

    def __init__(self):
        """Initialize DocumentAgent"""
        self.logger = logging.getLogger("DocumentAgent")
        self.llm_client = None  # Will be initialized when needed
        self.document_tool = DocumentGenerationTool()

        # LangGraph 0.6+ 설정
        self.memory = MemorySaver()
        self.graph = None
        self.app = None

        # 에이전트 설정
        self._setup_graph()

    def _setup_graph(self):
        """LangGraph 워크플로우 설정"""
        # 상태 그래프 생성
        workflow = StateGraph(DocumentAgentState)

        # 노드 추가
        workflow.add_node("analyze_request", self.analyze_request_node)
        workflow.add_node("validate_parameters", self.validate_parameters_node)
        workflow.add_node("generate_document", self.generate_document_node)
        workflow.add_node("format_output", self.format_output_node)

        # 엣지 설정
        workflow.set_entry_point("analyze_request")
        workflow.add_edge("analyze_request", "validate_parameters")
        workflow.add_conditional_edges(
            "validate_parameters",
            self.check_parameters,
            {
                "valid": "generate_document",
                "invalid": END
            }
        )
        workflow.add_edge("generate_document", "format_output")
        workflow.add_edge("format_output", END)

        # 컴파일
        self.graph = workflow
        self.app = workflow.compile(checkpointer=self.memory)

        self.logger.info("DocumentAgent graph compiled successfully")

    async def analyze_request_node(self, state: DocumentAgentState) -> DocumentAgentState:
        """요청 분석 노드"""
        try:
            query = state["original_query"]
            self.logger.info(f"Analyzing document request: {query}")

            # 간단한 문서 유형 감지 (LLM 없이)
            analysis = self._simple_analyze(query)

            # State 업데이트
            return {
                **state,
                "document_type": analysis.get("document_type", ""),
                "document_params": analysis.get("detected_params", {}),
                "required_params": analysis.get("required_params", []),
                "document_format": analysis.get("format", "TEXT"),
                "status": "analyzed"
            }

        except Exception as e:
            self.logger.error(f"Error analyzing request: {e}")
            return {
                **state,
                "status": "error",
                "error_message": str(e)
            }

    async def validate_parameters_node(self, state: DocumentAgentState) -> DocumentAgentState:
        """파라미터 검증 노드"""
        try:
            document_type = state.get("document_type")
            document_params = state.get("document_params", {})
            required_params = state.get("required_params", [])

            self.logger.info(f"Validating parameters for {document_type}")

            # 문서 유형 확인
            if not document_type:
                return {
                    **state,
                    "validation_errors": ["문서 유형을 확인할 수 없습니다"],
                    "status": "validation_failed"
                }

            # 필수 파라미터 확인
            missing_params = []
            for param in required_params:
                if param not in document_params:
                    missing_params.append(param)

            if missing_params:
                # 사용자에게 추가 정보 요청
                return {
                    **state,
                    "missing_params": missing_params,
                    "validation_errors": [f"다음 정보가 필요합니다: {', '.join(missing_params)}"],
                    "status": "needs_more_info"
                }

            return {
                **state,
                "status": "validated"
            }

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return {
                **state,
                "status": "error",
                "error_message": str(e)
            }

    def check_parameters(self, state: DocumentAgentState) -> str:
        """파라미터 검증 결과 확인"""
        status = state.get("status", "")
        if status == "validated":
            return "valid"
        else:
            return "invalid"

    async def generate_document_node(self, state: DocumentAgentState) -> DocumentAgentState:
        """문서 생성 노드"""
        try:
            document_type = state["document_type"]
            document_params = state.get("document_params", {})
            document_format = state.get("document_format", "TEXT")

            self.logger.info(f"Generating {document_type} in {document_format} format")

            # Document Generation Tool 호출
            result = await self.document_tool.search(
                query=state["original_query"],
                params={
                    "document_type": document_type,
                    "document_params": document_params,
                    "format": document_format
                }
            )

            if result["status"] == "success" and result["data"]:
                document_data = result["data"][0]
                return {
                    **state,
                    "generated_document": document_data,
                    "status": "generated"
                }
            else:
                return {
                    **state,
                    "status": "generation_failed",
                    "error_message": "문서 생성 실패"
                }

        except Exception as e:
            self.logger.error(f"Document generation error: {e}")
            return {
                **state,
                "status": "error",
                "error_message": str(e)
            }

    async def format_output_node(self, state: DocumentAgentState) -> DocumentAgentState:
        """출력 포맷팅 노드"""
        try:
            generated_document = state.get("generated_document")
            if not generated_document:
                return state

            document_format = state.get("document_format", "TEXT")
            self.logger.info(f"Formatting output as {document_format}")

            # 문서 요약 생성
            summary = f"""
문서가 성공적으로 생성되었습니다.

문서 유형: {generated_document.get('document_type', 'N/A')}
문서 ID: {generated_document.get('metadata', {}).get('document_id', 'N/A')}
생성 시간: {generated_document.get('metadata', {}).get('created_at', 'N/A')}
출력 형식: {document_format}
"""

            return {
                **state,
                "document_summary": summary,
                "status": "completed"
            }

        except Exception as e:
            self.logger.error(f"Formatting error: {e}")
            return {
                **state,
                "status": "error",
                "error_message": str(e)
            }

    def _simple_analyze(self, query: str) -> Dict[str, Any]:
        """Simple document type detection without LLM"""
        query_lower = query.lower()

        # Detect document type
        doc_type = None
        if "임대차" in query_lower or "월세" in query_lower:
            doc_type = "임대차계약서"
        elif "매매" in query_lower:
            doc_type = "매매계약서"
        elif "전세" in query_lower:
            doc_type = "전세계약서"
        elif "내용증명" in query_lower:
            doc_type = "내용증명"
        elif "계약해지" in query_lower:
            doc_type = "계약해지통지서"

        # Detect format
        format_type = "TEXT"
        if "html" in query_lower:
            format_type = "HTML"
        elif "json" in query_lower:
            format_type = "JSON"

        return {
            "document_type": doc_type,
            "required_params": [],
            "detected_params": {},
            "format": format_type
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        에이전트 실행

        Args:
            input_data: {
                "original_query": str,
                "document_type": Optional[str],
                "document_params": Optional[Dict],
                "document_format": Optional[str],
                "chat_session_id": str,
                "shared_context": Dict
            }

        Returns:
            실행 결과
        """
        try:
            self.logger.info(f"DocumentAgent executing with query: {input_data.get('original_query', '')}")

            # 초기 상태 설정
            initial_state = DocumentAgentState(
                chat_session_id=input_data.get("chat_session_id", ""),
                original_query=input_data.get("original_query", ""),
                document_type=input_data.get("document_type", ""),
                document_params=input_data.get("document_params", {}),
                document_format=input_data.get("document_format", "TEXT"),
                status="initialized",
                shared_context=input_data.get("shared_context", {}),
                todos=input_data.get("todos", []),
                todo_counter=input_data.get("todo_counter", 0),
                parent_todo_id=input_data.get("parent_todo_id"),
                generated_document=None,
                missing_params=[],
                required_params=[],
                validation_errors=[],
                template_id="",
                document_summary="",
                error_message=""
            )

            # LangGraph 실행
            config = {"configurable": {"thread_id": input_data.get("chat_session_id", "default")}}
            result = await self.app.ainvoke(initial_state, config)

            # 결과 반환
            return {
                "status": result.get("status", "unknown"),
                "generated_document": result.get("generated_document"),
                "document_summary": result.get("document_summary", ""),
                "document_type": result.get("document_type"),
                "document_format": result.get("document_format"),
                "missing_params": result.get("missing_params", []),
                "validation_errors": result.get("validation_errors", []),
                "error_message": result.get("error_message", ""),
                "todos": result.get("todos", [])
            }

        except Exception as e:
            self.logger.error(f"DocumentAgent execution error: {e}")
            return {
                "status": "error",
                "error_message": str(e),
                "todos": []
            }


# 테스트 코드
if __name__ == "__main__":
    import asyncio

    async def test():
        agent = DocumentAgent()

        # 테스트 1: 임대차계약서 생성
        print("\n=== Test 1: 임대차계약서 생성 ===")
        result = await agent.execute({
            "original_query": "서울 강남구 아파트 월세계약서 만들어줘. 보증금 5천만원, 월세 100만원",
            "chat_session_id": "test_session_1"
        })
        print(f"Status: {result['status']}")
        print(f"Document Type: {result.get('document_type')}")
        if result.get('document_summary'):
            print(f"Summary: {result['document_summary']}")

        # 테스트 2: 내용증명 생성
        print("\n=== Test 2: 내용증명 생성 ===")
        result = await agent.execute({
            "original_query": "임대료 인상을 알리는 내용증명 작성해줘",
            "chat_session_id": "test_session_2",
            "document_format": "HTML"
        })
        print(f"Status: {result['status']}")
        if result.get('validation_errors'):
            print(f"Validation Errors: {result['validation_errors']}")

        # 테스트 3: 파라미터 부족한 경우
        print("\n=== Test 3: 파라미터 부족 ===")
        result = await agent.execute({
            "original_query": "계약서 만들어줘",
            "chat_session_id": "test_session_3"
        })
        print(f"Status: {result['status']}")
        if result.get('missing_params'):
            print(f"Missing Parameters: {result['missing_params']}")

    asyncio.run(test())