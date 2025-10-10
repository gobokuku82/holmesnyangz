"""
주택임대차 표준계약서 생성 Tool
템플릿 기반으로 주택임대차 계약서를 생성
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class LeaseContractGeneratorTool:
    """
    주택임대차 표준계약서 생성 도구
    템플릿을 로드하여 계약서 필드를 채워 생성
    """

    def __init__(self, template_path: Optional[str] = None):
        """
        초기화

        Args:
            template_path: 템플릿 파일 경로 (선택적)
        """
        self.name = "lease_contract_generator"

        # 기본 템플릿 경로
        if template_path:
            self.template_path = Path(template_path)
        else:
            backend_dir = Path(__file__).parent.parent.parent.parent
            self.template_path = backend_dir / "data" / "storage" / "documents" / "주택임대차 표준계약서.docx"

        # 템플릿 내용 (fallback)
        self.template_content = None
        self._load_template()

        logger.info(f"LeaseContractGeneratorTool initialized with template: {self.template_path}")

    def _load_template(self):
        """템플릿 파일 로드"""
        try:
            if not self.template_path.exists():
                logger.warning(f"Template file not found: {self.template_path}")
                self.template_content = None
                return

            # docx 파일 로드 시도
            if self.template_path.suffix == ".docx":
                try:
                    from docx import Document
                    doc = Document(str(self.template_path))

                    # docx를 텍스트로 변환
                    full_text = []
                    for para in doc.paragraphs:
                        full_text.append(para.text)

                    self.template_content = "\n".join(full_text)
                    logger.info("Template loaded successfully from .docx")

                except ImportError:
                    logger.error("python-docx not installed. Cannot load .docx template")
                    self.template_content = None
                except Exception as e:
                    logger.error(f"Failed to load .docx template: {e}")
                    self.template_content = None

            # txt/md 파일 로드
            elif self.template_path.suffix in [".txt", ".md"]:
                with open(self.template_path, "r", encoding="utf-8") as f:
                    self.template_content = f.read()
                logger.info(f"Template loaded successfully from {self.template_path.suffix}")

            else:
                logger.warning(f"Unsupported template format: {self.template_path.suffix}")
                self.template_content = None

        except Exception as e:
            logger.error(f"Template loading failed: {e}")
            self.template_content = None

    async def execute(
        self,
        lessor: Optional[str] = None,
        lessee: Optional[str] = None,
        address: Optional[str] = None,
        deposit: Optional[str] = None,
        monthly_rent: Optional[str] = None,
        contract_period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        special_terms: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        주택임대차 계약서 생성

        Args:
            lessor: 임대인 (집주인)
            lessee: 임차인 (세입자)
            address: 임대물 주소
            deposit: 보증금
            monthly_rent: 월세
            contract_period: 계약기간
            start_date: 계약 시작일
            end_date: 계약 종료일
            special_terms: 특약사항
            **kwargs: 추가 파라미터

        Returns:
            생성된 계약서 정보
        """
        try:
            logger.info("Generating lease contract")

            # 템플릿 없는 경우 에러 안내
            if self.template_content is None:
                return {
                    "status": "error",
                    "error_type": "template_not_loaded",
                    "message": (
                        "주택임대차 표준계약서 템플릿을 로드할 수 없습니다.\n"
                        f"템플릿 파일 ({self.template_path})을 다음 형식으로 변환해주세요:\n"
                        "- .txt (텍스트 파일)\n"
                        "- .md (마크다운 파일)\n\n"
                        "또는 python-docx 라이브러리가 제대로 설치되어 있는지 확인해주세요."
                    ),
                    "template_path": str(self.template_path),
                    "timestamp": datetime.now().isoformat()
                }

            # 필드 값 준비
            fields = {
                "임대인": lessor or "[임대인명]",
                "임차인": lessee or "[임차인명]",
                "주소": address or "[임대물 주소]",
                "보증금": deposit or "[보증금 금액]",
                "월세": monthly_rent or "[월세 금액]",
                "계약기간": contract_period or f"{start_date or '[시작일]'} ~ {end_date or '[종료일]'}",
                "시작일": start_date or "[계약 시작일]",
                "종료일": end_date or "[계약 종료일]",
                "특약사항": special_terms or "[특약사항이 있는 경우 기재]",
                "작성일": datetime.now().strftime("%Y년 %m월 %d일")
            }

            # 템플릿에 필드 적용
            contract_content = self._fill_template(self.template_content, fields)

            # 계약서 메타데이터
            metadata = {
                "document_type": "주택임대차 표준계약서",
                "template_version": "v1.0",
                "generated_at": datetime.now().isoformat(),
                "fields_filled": {k: v for k, v in fields.items() if not v.startswith("[")}
            }

            return {
                "status": "success",
                "content": contract_content,
                "title": "주택임대차 표준계약서",
                "metadata": metadata,
                "fields": fields,
                "sections": self._extract_sections(contract_content),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Lease contract generation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _fill_template(self, template: str, fields: Dict[str, str]) -> str:
        """
        템플릿에 필드 값 채우기

        Args:
            template: 템플릿 텍스트
            fields: 채울 필드 딕셔너리

        Returns:
            필드가 채워진 계약서
        """
        content = template

        # 필드 치환 (여러 패턴 지원)
        for key, value in fields.items():
            # [필드명] 형식
            content = content.replace(f"[{key}]", value)
            # {필드명} 형식
            content = content.replace(f"{{{key}}}", value)
            # {{필드명}} 형식
            content = content.replace(f"{{{{{key}}}}}", value)

        return content

    def _extract_sections(self, content: str) -> list:
        """
        계약서 내용에서 섹션 추출

        Args:
            content: 계약서 전문

        Returns:
            섹션 리스트
        """
        sections = []
        current_section = None
        current_content = []

        for line in content.split("\n"):
            # 섹션 제목 감지 (예: "제1조", "1.", "가.", 등)
            if (line.strip().startswith("제") and "조" in line) or \
               (line.strip() and line.strip()[0].isdigit() and "." in line[:3]):

                # 이전 섹션 저장
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": "\n".join(current_content).strip()
                    })

                # 새 섹션 시작
                current_section = line.strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)

        # 마지막 섹션 저장
        if current_section:
            sections.append({
                "title": current_section,
                "content": "\n".join(current_content).strip()
            })

        return sections

    def get_required_fields(self) -> list:
        """필수 필드 목록 반환"""
        return ["lessor", "lessee", "address", "deposit", "monthly_rent", "start_date", "end_date"]

    def get_optional_fields(self) -> list:
        """선택 필드 목록 반환"""
        return ["special_terms", "utilities", "maintenance", "broker"]


# 테스트용
if __name__ == "__main__":
    import asyncio

    async def test_lease_contract_generator():
        tool = LeaseContractGeneratorTool()

        # 테스트 데이터
        test_params = {
            "lessor": "홍길동",
            "lessee": "김철수",
            "address": "서울특별시 강남구 테헤란로 123, 456호",
            "deposit": "5억원",
            "monthly_rent": "200만원",
            "start_date": "2024년 1월 1일",
            "end_date": "2026년 1월 1일",
            "contract_period": "2024년 1월 1일 ~ 2026년 1월 1일 (2년)",
            "special_terms": "반려동물 사육 가능"
        }

        result = await tool.execute(**test_params)

        print("=== Lease Contract Generation Result ===")
        print(f"Status: {result['status']}")

        if result['status'] == 'success':
            print(f"Title: {result['title']}")
            print(f"Sections: {len(result.get('sections', []))}")
            print(f"\n[Contract Preview]")
            print(result['content'][:500] + "...")
        else:
            print(f"Error: {result.get('error') or result.get('message')}")

    asyncio.run(test_lease_contract_generator())
