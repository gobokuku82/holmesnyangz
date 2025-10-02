"""
Document Generation Tool

문서 생성 도구 - 계약서, 신청서, 통지서 등 다양한 법률 문서를 생성합니다.
현재는 Mock 데이터를 사용하며, 추후 실제 템플릿 DB와 연동 예정입니다.
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from tools.base_tool import BaseTool


class DocumentGenerationTool(BaseTool):
    """문서 생성 도구"""

    def __init__(self):
        super().__init__(
            name="document_generation",
            description="계약서, 신청서, 통지서 등 법률 문서 생성",
            use_mock_data=True  # Always use mock data for now
        )
        self.tool_name = "document_generation"
        self.logger = logging.getLogger(__name__)

        # 지원하는 문서 유형
        self.supported_document_types = [
            "임대차계약서",
            "매매계약서",
            "전세계약서",
            "월세계약서",
            "근저당권설정계약서",
            "내용증명",
            "계약해지통지서",
            "임대료인상통지서",
            "보증금반환청구서"
        ]

        # 지원하는 출력 형식
        self.supported_formats = ["TEXT", "HTML", "JSON", "DOCX", "PDF"]

    async def search(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        문서 생성 요청 처리

        Args:
            query: 사용자 요청 (예: "임대차계약서 만들어줘")
            params: {
                "document_type": "임대차계약서",
                "document_params": {
                    "lessor_name": "김철수",
                    "lessee_name": "이영희",
                    "property_address": "서울시 강남구...",
                    "deposit": 10000000,
                    "monthly_rent": 500000,
                    "contract_period": "2년"
                },
                "format": "HTML"  # TEXT, HTML, JSON, DOCX, PDF
            }
        """
        try:
            params = params or {}
            document_type = params.get("document_type", self._detect_document_type(query))
            document_params = params.get("document_params", {})
            output_format = params.get("format", "TEXT").upper()

            self.logger.info(f"Document generation request: {document_type}, format: {output_format}")

            # 문서 유형 확인
            if not document_type:
                return self.format_results(
                    data=[{
                        "type": "error",
                        "message": "문서 유형을 지정해주세요",
                        "supported_types": self.supported_document_types
                    }],
                    total_count=0,
                    query=query
                )

            # 지원하는 문서 유형인지 확인
            if document_type not in self.supported_document_types:
                return self.format_results(
                    data=[{
                        "type": "error",
                        "message": f"'{document_type}'은(는) 지원하지 않는 문서 유형입니다",
                        "supported_types": self.supported_document_types
                    }],
                    total_count=0,
                    query=query
                )

            # Mock 데이터로 문서 생성
            generated_document = await self._generate_mock_document(
                document_type,
                document_params,
                output_format
            )

            return self.format_results(
                data=[generated_document],
                total_count=1,
                query=query
            )

        except Exception as e:
            self.logger.error(f"Document generation error: {e}")
            return self.format_results(
                data=[{
                    "type": "error",
                    "message": f"문서 생성 중 오류 발생: {str(e)}"
                }],
                total_count=0,
                query=query
            )

    def _detect_document_type(self, query: str) -> Optional[str]:
        """쿼리에서 문서 유형 감지"""
        query_lower = query.lower()

        type_keywords = {
            "임대차계약서": ["임대차", "임대차계약"],
            "매매계약서": ["매매계약", "매매"],
            "전세계약서": ["전세", "전세계약"],
            "월세계약서": ["월세", "월세계약"],
            "근저당권설정계약서": ["근저당", "근저당권"],
            "내용증명": ["내용증명"],
            "계약해지통지서": ["계약해지", "해지통지"],
            "임대료인상통지서": ["임대료인상", "월세인상"],
            "보증금반환청구서": ["보증금반환", "보증금청구"]
        }

        for doc_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return doc_type

        return None

    async def _generate_mock_document(
        self,
        document_type: str,
        params: Dict[str, Any],
        output_format: str
    ) -> Dict[str, Any]:
        """Mock 문서 생성"""

        # 기본 템플릿 가져오기
        template = self._get_mock_template(document_type)

        # 파라미터 적용
        document_content = self._apply_parameters(template, params)

        # 포맷 변환
        formatted_content = self._format_document(document_content, output_format)

        # 메타데이터 생성
        metadata = {
            "document_id": f"DOC_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "document_type": document_type,
            "created_at": datetime.now().isoformat(),
            "format": output_format,
            "parameters_used": list(params.keys()) if params else [],
            "template_version": "1.0.0",
            "is_mock": True  # Mock 데이터임을 표시
        }

        return {
            "type": "document",
            "document_type": document_type,
            "content": formatted_content,
            "metadata": metadata,
            "format": output_format,
            "message": f"{document_type} 문서가 생성되었습니다 (Mock 데이터)"
        }

    def _get_mock_template(self, document_type: str) -> str:
        """Mock 템플릿 반환"""
        templates = {
            "임대차계약서": """
부동산 임대차 계약서

임대인(이하 "갑"이라 한다)과 임차인(이하 "을"이라 한다)은 아래 표시 부동산에 관하여 다음과 같이 임대차계약을 체결한다.

제1조 (목적물의 표시)
소재지: {property_address}
구조 및 용도: {property_type}
임대면적: {property_area}㎡

제2조 (임대차 기간)
임대차 기간은 {start_date}부터 {end_date}까지 {contract_period}으로 한다.

제3조 (보증금과 월세)
1. 보증금: 금 {deposit}원
2. 월세: 금 {monthly_rent}원
3. 월세 납부일: 매월 {payment_date}일

제4조 (계약의 해지)
갑 또는 을이 이 계약상의 의무를 이행하지 않을 때에는 그 상대방은 계약을 해지할 수 있다.

제5조 (특약사항)
{special_terms}

위 계약을 증명하기 위하여 계약서 2통을 작성하여 갑, 을이 서명날인 후 각각 1통씩 보관한다.

계약일: {contract_date}

임대인(갑): {lessor_name}  (인)
주소: {lessor_address}
연락처: {lessor_phone}

임차인(을): {lessee_name}  (인)
주소: {lessee_address}
연락처: {lessee_phone}
""",
            "매매계약서": """
부동산 매매 계약서

매도인(이하 "갑"이라 한다)과 매수인(이하 "을"이라 한다)은 아래 표시 부동산에 관하여 다음과 같이 매매계약을 체결한다.

제1조 (목적물의 표시)
소재지: {property_address}
대지면적: {land_area}㎡
건물면적: {building_area}㎡
구조: {structure}

제2조 (매매대금)
매매대금은 금 {sale_price}원으로 한다.

제3조 (계약금과 잔금)
1. 계약금: 금 {down_payment}원은 계약시에 지불한다.
2. 중도금: 금 {middle_payment}원은 {middle_payment_date}에 지불한다.
3. 잔금: 금 {final_payment}원은 {final_payment_date}에 지불한다.

제4조 (소유권 이전)
갑은 잔금 수령과 동시에 을에게 소유권이전등기에 필요한 모든 서류를 교부한다.

제5조 (특약사항)
{special_terms}

계약일: {contract_date}

매도인(갑): {seller_name}  (인)
매수인(을): {buyer_name}  (인)
""",
            "내용증명": """
내용증명

발신인: {sender_name}
주소: {sender_address}

수신인: {receiver_name}
주소: {receiver_address}

제목: {subject}

{content}

위와 같이 통지합니다.

{send_date}

발신인: {sender_name} (인)
"""
        }

        # 기본 템플릿
        default_template = """
{document_type}

작성일: {created_date}

[문서 내용]
{content}

[서명]
작성자: {author_name}
"""

        return templates.get(document_type, default_template)

    def _apply_parameters(self, template: str, params: Dict[str, Any]) -> str:
        """템플릿에 파라미터 적용"""
        # 기본값 설정
        default_params = {
            "property_address": "[주소 입력 필요]",
            "property_type": "[건물 유형 입력 필요]",
            "property_area": "[면적 입력 필요]",
            "start_date": datetime.now().strftime("%Y년 %m월 %d일"),
            "end_date": "[종료일 입력 필요]",
            "contract_period": "[계약기간 입력 필요]",
            "deposit": "[보증금 입력 필요]",
            "monthly_rent": "[월세 입력 필요]",
            "payment_date": "[납부일 입력 필요]",
            "contract_date": datetime.now().strftime("%Y년 %m월 %d일"),
            "lessor_name": "[임대인 이름]",
            "lessor_address": "[임대인 주소]",
            "lessor_phone": "[임대인 연락처]",
            "lessee_name": "[임차인 이름]",
            "lessee_address": "[임차인 주소]",
            "lessee_phone": "[임차인 연락처]",
            "special_terms": "[특약사항 없음]",
            "created_date": datetime.now().strftime("%Y년 %m월 %d일"),
            "content": "[내용 입력 필요]",
            "author_name": "[작성자명]",
            "document_type": "[문서 유형]"
        }

        # 사용자 파라미터로 업데이트
        default_params.update(params)

        # 템플릿 채우기
        try:
            return template.format(**default_params)
        except KeyError as e:
            # 누락된 키는 기본값으로 대체
            for key in template.replace("{", " {").replace("}", "} ").split():
                if key.startswith("{") and key.endswith("}"):
                    param_name = key[1:-1]
                    if param_name not in default_params:
                        default_params[param_name] = f"[{param_name} 입력 필요]"

            return template.format(**default_params)

    def _format_document(self, content: str, output_format: str) -> Any:
        """문서를 지정된 형식으로 변환"""
        if output_format == "TEXT":
            return content

        elif output_format == "HTML":
            html_content = content.replace("\n", "<br>\n")
            return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>법률 문서</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .content {{ white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="content">{html_content}</div>
</body>
</html>"""

        elif output_format == "JSON":
            lines = content.split("\n")
            sections = []
            current_section = {"title": "", "content": []}

            for line in lines:
                if line.strip() and (line.startswith("제") or line.strip().endswith("계약서")):
                    if current_section["content"]:
                        sections.append(current_section)
                    current_section = {"title": line.strip(), "content": []}
                else:
                    if line.strip():
                        current_section["content"].append(line.strip())

            if current_section["content"]:
                sections.append(current_section)

            return {
                "document": {
                    "sections": sections,
                    "raw_text": content
                }
            }

        elif output_format in ["DOCX", "PDF"]:
            # 실제 구현시 python-docx, reportlab 등 사용
            return {
                "format": output_format,
                "content": content,
                "message": f"{output_format} 형식은 추후 구현 예정입니다. 현재는 TEXT 형식으로 제공됩니다."
            }

        else:
            return content

    async def get_mock_data(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """BaseTool abstract method implementation - not used but required"""
        # This tool doesn't use the mock data pattern from BaseTool
        # It has its own mock document generation system
        return await self.search(query, params)

    def get_capabilities(self) -> Dict[str, Any]:
        """도구의 기능 정보 반환"""
        return {
            "tool_name": self.tool_name,
            "description": self.description,
            "supported_document_types": self.supported_document_types,
            "supported_formats": self.supported_formats,
            "parameters": {
                "document_type": "생성할 문서 유형",
                "document_params": "문서 생성에 필요한 파라미터들",
                "format": "출력 형식 (TEXT, HTML, JSON, DOCX, PDF)"
            },
            "is_mock": True,
            "version": "1.0.0"
        }


# 테스트 코드
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = DocumentGenerationTool()

        # 테스트 1: 임대차계약서 생성
        print("\n=== Test 1: 임대차계약서 생성 ===")
        result = await tool.search(
            "임대차계약서 만들어줘",
            {
                "document_type": "임대차계약서",
                "document_params": {
                    "property_address": "서울시 강남구 테헤란로 123",
                    "deposit": "100,000,000",
                    "monthly_rent": "1,000,000",
                    "lessor_name": "김철수",
                    "lessee_name": "이영희"
                },
                "format": "TEXT"
            }
        )
        print(f"Status: {result['status']}")
        if result['data']:
            print(f"Document Type: {result['data'][0].get('document_type')}")
            print(f"Content Preview: {result['data'][0].get('content', '')[:200]}...")

        # 테스트 2: 내용증명 생성 (HTML)
        print("\n=== Test 2: 내용증명 생성 (HTML) ===")
        result = await tool.search(
            "내용증명 작성해줘",
            {
                "document_type": "내용증명",
                "document_params": {
                    "sender_name": "홍길동",
                    "receiver_name": "김대표",
                    "subject": "임대료 인상 통보",
                    "content": "임대차계약서 제5조에 따라 임대료를 인상합니다."
                },
                "format": "HTML"
            }
        )
        print(f"Status: {result['status']}")
        if result['data']:
            print(f"Format: {result['data'][0].get('format')}")

        # 테스트 3: 지원하지 않는 문서
        print("\n=== Test 3: 지원하지 않는 문서 ===")
        result = await tool.search("특허출원서 작성해줘")
        print(f"Status: {result['status']}")
        if result['data']:
            print(f"Error: {result['data'][0].get('message')}")

    asyncio.run(test())