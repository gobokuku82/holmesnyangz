"""
문서 청킹 모듈
- 의미 기반 청킹
- 표 구조 보존 청킹
- 오버랩 처리
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import tiktoken
import logging

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    """청크 데이터 클래스"""
    content: str
    chunk_id: str
    doc_id: str
    chunk_index: int
    chunk_type: str  # table, text, mixed
    metadata: Dict[str, Any]
    token_count: int
    char_count: int
    overlap_with_previous: bool = False
    overlap_with_next: bool = False

class DocumentChunker:
    """문서 청킹 클래스"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
        tokenizer_model: str = "cl100k_base"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # 토크나이저 초기화
        try:
            self.tokenizer = tiktoken.get_encoding(tokenizer_model)
        except:
            logger.warning(f"Failed to load {tokenizer_model}, using default")
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # 청킹 구분자 (우선순위 순)
        self.separators = [
            "\n\n[TABLE]",  # 표 구분자
            "\n[/TABLE]\n",  # 표 종료
            "\n\n",  # 이중 개행
            "\n",    # 단일 개행
            ". ",    # 문장 끝
            ", ",    # 쉼표
            " ",     # 공백
        ]
    
    def chunk_document(
        self, 
        processed_data: Dict[str, Any], 
        doc_id: str
    ) -> List[Chunk]:
        """문서 전체를 청킹"""
        chunks = []
        
        # 구조화된 콘텐츠 기반 청킹
        if 'structured_content' in processed_data:
            chunks = self._chunk_structured_content(
                processed_data['structured_content'], 
                doc_id
            )
        else:
            # 일반 텍스트 청킹
            all_text = self._extract_all_text(processed_data)
            chunks = self._chunk_text(all_text, doc_id)
        
        # 오버랩 처리
        chunks = self._add_overlaps(chunks)
        
        return chunks
    
    def _chunk_structured_content(
        self, 
        structured_content: List[Dict], 
        doc_id: str
    ) -> List[Chunk]:
        """구조화된 콘텐츠 청킹"""
        chunks = []
        chunk_index = 0
        
        for item in structured_content:
            if item['type'] == 'table':
                # 표는 하나의 청크로 처리 (크기가 크면 행 단위로 분할)
                table_chunks = self._chunk_table(
                    item['content'], 
                    doc_id, 
                    chunk_index
                )
                chunks.extend(table_chunks)
                chunk_index += len(table_chunks)
                
            elif item['type'] == 'text':
                # 텍스트 청킹
                text = item['content'].get('cleaned', '')
                if text:
                    text_chunks = self._chunk_text_content(
                        text, 
                        doc_id, 
                        chunk_index,
                        metadata=item['content']
                    )
                    chunks.extend(text_chunks)
                    chunk_index += len(text_chunks)
        
        return chunks
    
    def _chunk_table(
        self, 
        table_data: Dict, 
        doc_id: str, 
        start_index: int
    ) -> List[Chunk]:
        """표 데이터 청킹"""
        chunks = []
        
        # 전체 표 텍스트
        table_text = table_data.get('formatted_text', '')
        token_count = self._count_tokens(table_text)
        
        # 표가 작으면 하나의 청크로
        if token_count <= self.chunk_size:
            chunk = Chunk(
                content=table_text,
                chunk_id=f"{doc_id}_chunk_{start_index}",
                doc_id=doc_id,
                chunk_index=start_index,
                chunk_type='table',
                metadata={
                    'headers': table_data.get('headers', []),
                    'row_count': len(table_data.get('rows', [])),
                    'is_complete_table': True
                },
                token_count=token_count,
                char_count=len(table_text)
            )
            chunks.append(chunk)
        else:
            # 표가 크면 행 단위로 분할
            chunks = self._split_large_table(
                table_data, 
                doc_id, 
                start_index
            )
        
        return chunks
    
    def _split_large_table(
        self, 
        table_data: Dict, 
        doc_id: str, 
        start_index: int
    ) -> List[Chunk]:
        """큰 표를 행 단위로 분할"""
        chunks = []
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        
        current_chunk_rows = []
        current_tokens = 0
        chunk_index = start_index
        
        # 헤더 텍스트 (모든 청크에 포함)
        header_text = f"[표 헤더: {', '.join(headers)}]\n"
        header_tokens = self._count_tokens(header_text)
        
        for row in rows:
            row_text = self._format_table_row(headers, row)
            row_tokens = self._count_tokens(row_text)
            
            # 현재 청크에 추가 가능한지 확인
            if current_tokens + row_tokens + header_tokens <= self.chunk_size:
                current_chunk_rows.append(row_text)
                current_tokens += row_tokens
            else:
                # 현재 청크 저장
                if current_chunk_rows:
                    chunk_content = header_text + '\n'.join(current_chunk_rows)
                    chunk = Chunk(
                        content=chunk_content,
                        chunk_id=f"{doc_id}_chunk_{chunk_index}",
                        doc_id=doc_id,
                        chunk_index=chunk_index,
                        chunk_type='table_partial',
                        metadata={
                            'headers': headers,
                            'row_count': len(current_chunk_rows),
                            'is_complete_table': False,
                            'part_of_table': True
                        },
                        token_count=current_tokens + header_tokens,
                        char_count=len(chunk_content)
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # 새 청크 시작
                current_chunk_rows = [row_text]
                current_tokens = row_tokens
        
        # 마지막 청크 저장
        if current_chunk_rows:
            chunk_content = header_text + '\n'.join(current_chunk_rows)
            chunk = Chunk(
                content=chunk_content,
                chunk_id=f"{doc_id}_chunk_{chunk_index}",
                doc_id=doc_id,
                chunk_index=chunk_index,
                chunk_type='table_partial',
                metadata={
                    'headers': headers,
                    'row_count': len(current_chunk_rows),
                    'is_complete_table': False,
                    'part_of_table': True
                },
                token_count=current_tokens + header_tokens,
                char_count=len(chunk_content)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _format_table_row(self, headers: List[str], row: List[str]) -> str:
        """표 행을 텍스트로 포맷팅"""
        formatted = []
        for header, cell in zip(headers, row):
            if header and cell:
                formatted.append(f"{header}: {cell}")
        return ' | '.join(formatted)
    
    def _chunk_text_content(
        self, 
        text: str, 
        doc_id: str, 
        start_index: int,
        metadata: Dict = None
    ) -> List[Chunk]:
        """텍스트 콘텐츠 청킹"""
        chunks = []
        
        # 의미 단위로 분할
        segments = self._split_by_separators(text)
        
        current_chunk = []
        current_tokens = 0
        chunk_index = start_index
        
        for segment in segments:
            segment_tokens = self._count_tokens(segment)
            
            # 단일 세그먼트가 너무 큰 경우
            if segment_tokens > self.chunk_size:
                # 현재 청크 저장
                if current_chunk:
                    chunk_content = ''.join(current_chunk)
                    chunks.append(self._create_chunk(
                        chunk_content, doc_id, chunk_index, 'text', metadata
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_tokens = 0
                
                # 큰 세그먼트를 강제 분할
                sub_chunks = self._force_split_segment(
                    segment, doc_id, chunk_index, metadata
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                
            # 현재 청크에 추가 가능
            elif current_tokens + segment_tokens <= self.chunk_size:
                current_chunk.append(segment)
                current_tokens += segment_tokens
                
            # 새 청크 필요
            else:
                # 현재 청크 저장
                if current_chunk:
                    chunk_content = ''.join(current_chunk)
                    chunks.append(self._create_chunk(
                        chunk_content, doc_id, chunk_index, 'text', metadata
                    ))
                    chunk_index += 1
                
                # 새 청크 시작
                current_chunk = [segment]
                current_tokens = segment_tokens
        
        # 마지막 청크 저장
        if current_chunk:
            chunk_content = ''.join(current_chunk)
            # 최소 크기 확인
            if self._count_tokens(chunk_content) >= self.min_chunk_size:
                chunks.append(self._create_chunk(
                    chunk_content, doc_id, chunk_index, 'text', metadata
                ))
            elif chunks:
                # 너무 작으면 이전 청크와 병합
                chunks[-1].content += '\n' + chunk_content
                chunks[-1].token_count = self._count_tokens(chunks[-1].content)
                chunks[-1].char_count = len(chunks[-1].content)
        
        return chunks
    
    def _split_by_separators(self, text: str) -> List[str]:
        """구분자를 사용한 텍스트 분할"""
        segments = [text]
        
        for separator in self.separators:
            new_segments = []
            for segment in segments:
                if separator in segment:
                    parts = segment.split(separator)
                    for i, part in enumerate(parts):
                        if part:
                            # 구분자 복원 (마지막 부분 제외)
                            if i < len(parts) - 1:
                                new_segments.append(part + separator)
                            else:
                                new_segments.append(part)
                else:
                    new_segments.append(segment)
            segments = new_segments
        
        return [s for s in segments if s.strip()]
    
    def _force_split_segment(
        self, 
        segment: str, 
        doc_id: str, 
        start_index: int,
        metadata: Dict = None
    ) -> List[Chunk]:
        """큰 세그먼트 강제 분할"""
        chunks = []
        words = segment.split()
        
        current_chunk = []
        current_tokens = 0
        chunk_index = start_index
        
        for word in words:
            word_tokens = self._count_tokens(word + ' ')
            
            if current_tokens + word_tokens <= self.chunk_size:
                current_chunk.append(word)
                current_tokens += word_tokens
            else:
                if current_chunk:
                    chunk_content = ' '.join(current_chunk)
                    chunks.append(self._create_chunk(
                        chunk_content, doc_id, chunk_index, 'text_forced_split', metadata
                    ))
                    chunk_index += 1
                
                current_chunk = [word]
                current_tokens = word_tokens
        
        if current_chunk:
            chunk_content = ' '.join(current_chunk)
            chunks.append(self._create_chunk(
                chunk_content, doc_id, chunk_index, 'text_forced_split', metadata
            ))
        
        return chunks
    
    def _add_overlaps(self, chunks: List[Chunk]) -> List[Chunk]:
        """청크 간 오버랩 추가"""
        if not chunks or self.chunk_overlap <= 0:
            return chunks
        
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            # 현재 청크의 끝 부분 추출
            current_words = current_chunk.content.split()
            overlap_words = current_words[-self.chunk_overlap:] if len(current_words) > self.chunk_overlap else current_words
            
            # 다음 청크의 시작 부분 추출
            next_words = next_chunk.content.split()
            overlap_start = next_words[:self.chunk_overlap] if len(next_words) > self.chunk_overlap else next_words
            
            # 오버랩 정보 추가
            current_chunk.overlap_with_next = True
            next_chunk.overlap_with_previous = True
            
            # 메타데이터에 오버랩 정보 추가
            current_chunk.metadata['overlap_next'] = ' '.join(overlap_start)
            next_chunk.metadata['overlap_prev'] = ' '.join(overlap_words)
        
        return chunks
    
    def _create_chunk(
        self, 
        content: str, 
        doc_id: str, 
        chunk_index: int, 
        chunk_type: str,
        metadata: Dict = None
    ) -> Chunk:
        """청크 객체 생성"""
        return Chunk(
            content=content.strip(),
            chunk_id=f"{doc_id}_chunk_{chunk_index}",
            doc_id=doc_id,
            chunk_index=chunk_index,
            chunk_type=chunk_type,
            metadata=metadata or {},
            token_count=self._count_tokens(content),
            char_count=len(content)
        )
    
    def _count_tokens(self, text: str) -> int:
        """토큰 수 계산"""
        return len(self.tokenizer.encode(text))
    
    def _extract_all_text(self, processed_data: Dict) -> str:
        """전체 텍스트 추출"""
        all_text = []
        
        # 표 텍스트
        for table in processed_data.get('tables', []):
            all_text.append(table.get('formatted_text', ''))
        
        # 단락 텍스트
        for para in processed_data.get('paragraphs', []):
            all_text.append(para.get('cleaned', ''))
        
        return '\n\n'.join(all_text)
    
    def print_chunking_summary(self, chunks: List[Chunk]):
        """청킹 결과 요약 출력"""
        print("\n" + "="*50)
        print("📦 청킹 결과")
        print("="*50)
        print(f"총 청크 수: {len(chunks)}")
        
        # 청크 타입별 통계
        chunk_types = {}
        for chunk in chunks:
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
        
        print("\n청크 타입별 분포:")
        for chunk_type, count in chunk_types.items():
            print(f"  - {chunk_type}: {count}개")
        
        # 토큰 통계
        token_counts = [c.token_count for c in chunks]
        if token_counts:
            print(f"\n토큰 통계:")
            print(f"  - 평균: {sum(token_counts) / len(token_counts):.1f}")
            print(f"  - 최소: {min(token_counts)}")
            print(f"  - 최대: {max(token_counts)}")
        
        # 샘플 청크
        if chunks:
            print(f"\n📄 첫 번째 청크 샘플:")
            print(f"  ID: {chunks[0].chunk_id}")
            print(f"  타입: {chunks[0].chunk_type}")
            print(f"  토큰: {chunks[0].token_count}")
            print(f"  내용: {chunks[0].content[:100]}...")
        
        print("="*50)
    
    def save_chunks(self, chunks: List[Chunk], output_path: str):
        """청크 저장"""
        import json
        from pathlib import Path
        
        output_path = Path(output_path)
        
        # JSON으로 저장
        chunks_data = []
        for chunk in chunks:
            chunks_data.append({
                'chunk_id': chunk.chunk_id,
                'doc_id': chunk.doc_id,
                'chunk_index': chunk.chunk_index,
                'content': chunk.content,
                'chunk_type': chunk.chunk_type,
                'metadata': chunk.metadata,
                'token_count': chunk.token_count,
                'char_count': chunk.char_count
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Chunks saved to {output_path}")
