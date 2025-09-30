"""
  
-   
-    
-  
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import tiktoken
import logging

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    """  """
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
    """  """
    
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
        
        #  
        try:
            self.tokenizer = tiktoken.get_encoding(tokenizer_model)
        except:
            logger.warning(f"Failed to load {tokenizer_model}, using default")
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        #   ( )
        self.separators = [
            "\n\n[TABLE]",  #  
            "\n[/TABLE]\n",  #  
            "\n\n",  #  
            "\n",    #  
            ". ",    #  
            ", ",    # 
            " ",     # 
        ]
    
    def chunk_document(
        self, 
        processed_data: Dict[str, Any], 
        doc_id: str
    ) -> List[Chunk]:
        """  """
        chunks = []
        
        #    
        if 'structured_content' in processed_data:
            chunks = self._chunk_structured_content(
                processed_data['structured_content'], 
                doc_id
            )
        else:
            #   
            all_text = self._extract_all_text(processed_data)
            chunks = self._chunk_text(all_text, doc_id)
        
        #  
        chunks = self._add_overlaps(chunks)
        
        return chunks
    
    def _chunk_structured_content(
        self, 
        structured_content: List[Dict], 
        doc_id: str
    ) -> List[Chunk]:
        """  """
        chunks = []
        chunk_index = 0
        
        for item in structured_content:
            if item['type'] == 'table':
                #     (    )
                table_chunks = self._chunk_table(
                    item['content'], 
                    doc_id, 
                    chunk_index
                )
                chunks.extend(table_chunks)
                chunk_index += len(table_chunks)
                
            elif item['type'] == 'text':
                #  
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
        """  """
        chunks = []
        
        #   
        table_text = table_data.get('formatted_text', '')
        token_count = self._count_tokens(table_text)
        
        #    
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
            #     
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
        """    """
        chunks = []
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])
        
        current_chunk_rows = []
        current_tokens = 0
        chunk_index = start_index
        
        #   (  )
        header_text = f"[ : {', '.join(headers)}]\n"
        header_tokens = self._count_tokens(header_text)
        
        for row in rows:
            row_text = self._format_table_row(headers, row)
            row_tokens = self._count_tokens(row_text)
            
            #     
            if current_tokens + row_tokens + header_tokens <= self.chunk_size:
                current_chunk_rows.append(row_text)
                current_tokens += row_tokens
            else:
                #   
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
                
                #   
                current_chunk_rows = [row_text]
                current_tokens = row_tokens
        
        #   
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
        """   """
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
        """  """
        chunks = []
        
        #   
        segments = self._split_by_separators(text)
        
        current_chunk = []
        current_tokens = 0
        chunk_index = start_index
        
        for segment in segments:
            segment_tokens = self._count_tokens(segment)
            
            #     
            if segment_tokens > self.chunk_size:
                #   
                if current_chunk:
                    chunk_content = ''.join(current_chunk)
                    chunks.append(self._create_chunk(
                        chunk_content, doc_id, chunk_index, 'text', metadata
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_tokens = 0
                
                #    
                sub_chunks = self._force_split_segment(
                    segment, doc_id, chunk_index, metadata
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                
            #    
            elif current_tokens + segment_tokens <= self.chunk_size:
                current_chunk.append(segment)
                current_tokens += segment_tokens
                
            #   
            else:
                #   
                if current_chunk:
                    chunk_content = ''.join(current_chunk)
                    chunks.append(self._create_chunk(
                        chunk_content, doc_id, chunk_index, 'text', metadata
                    ))
                    chunk_index += 1
                
                #   
                current_chunk = [segment]
                current_tokens = segment_tokens
        
        #   
        if current_chunk:
            chunk_content = ''.join(current_chunk)
            #   
            if self._count_tokens(chunk_content) >= self.min_chunk_size:
                chunks.append(self._create_chunk(
                    chunk_content, doc_id, chunk_index, 'text', metadata
                ))
            elif chunks:
                #     
                chunks[-1].content += '\n' + chunk_content
                chunks[-1].token_count = self._count_tokens(chunks[-1].content)
                chunks[-1].char_count = len(chunks[-1].content)
        
        return chunks
    
    def _split_by_separators(self, text: str) -> List[str]:
        """   """
        segments = [text]
        
        for separator in self.separators:
            new_segments = []
            for segment in segments:
                if separator in segment:
                    parts = segment.split(separator)
                    for i, part in enumerate(parts):
                        if part:
                            #   (  )
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
        """   """
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
        """   """
        if not chunks or self.chunk_overlap <= 0:
            return chunks
        
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            #     
            current_words = current_chunk.content.split()
            overlap_words = current_words[-self.chunk_overlap:] if len(current_words) > self.chunk_overlap else current_words
            
            #     
            next_words = next_chunk.content.split()
            overlap_start = next_words[:self.chunk_overlap] if len(next_words) > self.chunk_overlap else next_words
            
            #   
            current_chunk.overlap_with_next = True
            next_chunk.overlap_with_previous = True
            
            #    
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
        """  """
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
        """  """
        return len(self.tokenizer.encode(text))
    
    def _extract_all_text(self, processed_data: Dict) -> str:
        """  """
        all_text = []
        
        #  
        for table in processed_data.get('tables', []):
            all_text.append(table.get('formatted_text', ''))
        
        #  
        for para in processed_data.get('paragraphs', []):
            all_text.append(para.get('cleaned', ''))
        
        return '\n\n'.join(all_text)
    
    def print_chunking_summary(self, chunks: List[Chunk]):
        """   """
        print("\n" + "="*50)
        print("  ")
        print("="*50)
        print(f"  : {len(chunks)}")
        
        #   
        chunk_types = {}
        for chunk in chunks:
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
        
        print("\n  :")
        for chunk_type, count in chunk_types.items():
            print(f"  - {chunk_type}: {count}")
        
        #  
        token_counts = [c.token_count for c in chunks]
        if token_counts:
            print(f"\n :")
            print(f"  - : {sum(token_counts) / len(token_counts):.1f}")
            print(f"  - : {min(token_counts)}")
            print(f"  - : {max(token_counts)}")
        
        #  
        if chunks:
            print(f"\n    :")
            print(f"  ID: {chunks[0].chunk_id}")
            print(f"  : {chunks[0].chunk_type}")
            print(f"  : {chunks[0].token_count}")
            print(f"  : {chunks[0].content[:100]}...")
        
        print("="*50)
    
    def save_chunks(self, chunks: List[Chunk], output_path: str):
        """ """
        import json
        from pathlib import Path
        
        output_path = Path(output_path)
        
        # JSON 
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
