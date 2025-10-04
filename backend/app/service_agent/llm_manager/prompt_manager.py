"""
Prompt Manager - 프롬프트 템플릿 관리
프롬프트 파일 로딩, 변수 치환, 캐싱 담당
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)


class PromptManager:
    """
    프롬프트 템플릿 관리자
    - TXT/YAML 파일 로드
    - 변수 치환
    - 프롬프트 캐싱
    """

    def __init__(self, prompts_dir: Path = None):
        """
        초기화

        Args:
            prompts_dir: 프롬프트 디렉토리 (None이면 기본 경로)
        """
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / "prompts"

        self.prompts_dir = prompts_dir
        self._cache: Dict[str, str] = {}  # 프롬프트 캐시
        self._metadata_cache: Dict[str, Dict] = {}  # 메타데이터 캐시

        logger.debug(f"PromptManager initialized with directory: {self.prompts_dir}")

    def get(
        self,
        prompt_name: str,
        variables: Dict[str, Any] = None,
        category: str = None
    ) -> str:
        """
        프롬프트 로드 및 변수 치환

        Args:
            prompt_name: 프롬프트 이름 (예: "intent_analysis")
            variables: 치환할 변수 (예: {"query": "전세 계약은?"})
            category: 카테고리 (cognitive/execution/common, None이면 자동 탐색)

        Returns:
            완성된 프롬프트 문자열
        """
        variables = variables or {}

        # 프롬프트 템플릿 로드 (캐싱 활용)
        template = self._load_template(prompt_name, category)

        # 변수 치환
        try:
            prompt = template.format(**variables)
            return prompt
        except KeyError as e:
            logger.error(f"Missing variable in prompt {prompt_name}: {e}")
            raise ValueError(f"Missing required variable {e} for prompt '{prompt_name}'")

    def get_with_metadata(
        self,
        prompt_name: str,
        variables: Dict[str, Any] = None,
        category: str = None
    ) -> Dict[str, Any]:
        """
        프롬프트와 메타데이터를 함께 반환

        Args:
            prompt_name: 프롬프트 이름
            variables: 치환할 변수
            category: 카테고리

        Returns:
            {"prompt": "...", "metadata": {...}}
        """
        # 프롬프트 로드
        prompt = self.get(prompt_name, variables, category)

        # 메타데이터 로드 (YAML 파일인 경우)
        metadata = self._metadata_cache.get(prompt_name, {})

        return {
            "prompt": prompt,
            "metadata": metadata
        }

    def _load_template(self, prompt_name: str, category: str = None) -> str:
        """
        프롬프트 템플릿 파일 로드 (캐싱)

        Args:
            prompt_name: 프롬프트 이름
            category: 카테고리 (None이면 자동 탐색)

        Returns:
            프롬프트 템플릿 문자열
        """
        # 캐시 확인
        cache_key = f"{category or 'auto'}:{prompt_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 파일 경로 탐색
        file_path = self._find_prompt_file(prompt_name, category)

        if not file_path:
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_name} "
                f"(searched in {self.prompts_dir})"
            )

        # 파일 로드
        template = self._load_file(file_path)

        # 캐시 저장
        self._cache[cache_key] = template

        logger.debug(f"Loaded prompt template: {prompt_name} from {file_path}")

        return template

    def _find_prompt_file(self, prompt_name: str, category: str = None) -> Optional[Path]:
        """
        프롬프트 파일 경로 찾기

        Args:
            prompt_name: 프롬프트 이름
            category: 카테고리 (None이면 전체 탐색)

        Returns:
            파일 경로 (없으면 None)
        """
        # 검색할 카테고리 목록
        if category:
            categories = [category]
        else:
            categories = ["cognitive", "execution", "common"]

        # 각 카테고리에서 TXT, YAML 순서로 탐색
        for cat in categories:
            for ext in [".txt", ".yaml"]:
                file_path = self.prompts_dir / cat / f"{prompt_name}{ext}"
                if file_path.exists():
                    return file_path

        return None

    def _load_file(self, file_path: Path) -> str:
        """
        프롬프트 파일 로드 (TXT 또는 YAML)

        Args:
            file_path: 파일 경로

        Returns:
            프롬프트 템플릿 문자열
        """
        if file_path.suffix == ".txt":
            # TXT 파일: 그대로 로드
            return file_path.read_text(encoding='utf-8')

        elif file_path.suffix == ".yaml":
            # YAML 파일: 파싱 후 system_prompt 추출
            data = yaml.safe_load(file_path.read_text(encoding='utf-8'))

            # 메타데이터 캐싱
            prompt_name = file_path.stem
            self._metadata_cache[prompt_name] = data.get("metadata", {})

            # 프롬프트 반환
            return data.get("system_prompt", "")

        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

    def list_prompts(self, category: str = None) -> Dict[str, list]:
        """
        사용 가능한 프롬프트 목록 반환

        Args:
            category: 특정 카테고리만 (None이면 전체)

        Returns:
            {"cognitive": [...], "execution": [...], "common": [...]}
        """
        result = {}

        categories = [category] if category else ["cognitive", "execution", "common"]

        for cat in categories:
            cat_dir = self.prompts_dir / cat
            if cat_dir.exists():
                prompts = [
                    f.stem for f in cat_dir.iterdir()
                    if f.suffix in [".txt", ".yaml"]
                ]
                result[cat] = sorted(prompts)

        return result

    def reload(self):
        """캐시 초기화 (프롬프트 재로드 강제)"""
        self._cache.clear()
        self._metadata_cache.clear()
        logger.info("Prompt cache cleared")

    def validate(self, prompt_name: str, required_variables: list = None) -> bool:
        """
        프롬프트 유효성 검증

        Args:
            prompt_name: 프롬프트 이름
            required_variables: 필수 변수 목록

        Returns:
            유효하면 True
        """
        try:
            # 프롬프트 로드 시도
            template = self._load_template(prompt_name)

            # 필수 변수 확인
            if required_variables:
                import string
                formatter = string.Formatter()
                template_vars = [
                    field_name for _, field_name, _, _
                    in formatter.parse(template)
                    if field_name
                ]

                for var in required_variables:
                    if var not in template_vars:
                        logger.error(f"Required variable '{var}' not found in {prompt_name}")
                        return False

            return True

        except Exception as e:
            logger.error(f"Prompt validation failed for {prompt_name}: {e}")
            return False


# ============ 편의 함수 ============

def get_prompt(prompt_name: str, variables: Dict[str, Any] = None) -> str:
    """
    프롬프트 가져오기 (전역 편의 함수)

    Args:
        prompt_name: 프롬프트 이름
        variables: 변수

    Returns:
        완성된 프롬프트
    """
    manager = PromptManager()
    return manager.get(prompt_name, variables)
