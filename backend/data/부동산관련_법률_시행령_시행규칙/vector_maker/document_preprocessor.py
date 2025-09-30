"""
  
-   
-  
-   
"""
import re
from typing import List, Dict, Any, Tuple
import docx
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DocumentPreprocessor:
    """ """
    
    def __init__(self):
        self.cleaning_patterns = {
            'whitespace': r'\s+',
            'special_chars': r'[^\w\s-.,;:()\[\]\-/]',
            'repeated_dots': r'\.{3,}',
            'parenthesis_numbers': r'\(\d+\)',
            'bullet_points': r'^[\-\*\•]\s*',
        }
    
    def preprocess(self, file_path: str, structure_info: Dict = None) -> Dict[str, Any]:
        """   """
        doc = docx.Document(file_path)
        
        processed_data = {
            'tables': [],
            'paragraphs': [],
            'structured_content': [],
            'metadata': {}
        }
        
        #  
        for table in doc.tables:
            processed_table = self._process_table(table)
            if processed_table:
                processed_data['tables'].append(processed_table)
                processed_data['structured_content'].append({
                    'type': 'table',
                    'content': processed_table
                })
        
        #  
        for para in doc.paragraphs:
            processed_text = self._process_paragraph(para)
            if processed_text:
                processed_data['paragraphs'].append(processed_text)
                processed_data['structured_content'].append({
                    'type': 'text',
                    'content': processed_text
                })
        
        return processed_data
    
    def _process_table(self, table) -> Dict[str, Any]:
        """  """
        processed_table = {
            'headers': [],
            'rows': [],
            'formatted_text': '',
            'structured_data': []
        }
        
        #  
        if len(table.rows) > 0:
            headers = []
            for cell in table.rows[0].cells:
                header = self._clean_text(cell.text)
                headers.append(header)
            processed_table['headers'] = headers
        
        #   
        for row_idx, row in enumerate(table.rows[1:]):
            row_data = []
            row_dict = {}
            
            for col_idx, cell in enumerate(row.cells):
                cell_text = self._clean_text(cell.text)
                row_data.append(cell_text)
                
                if col_idx < len(processed_table['headers']):
                    header = processed_table['headers'][col_idx]
                    row_dict[header] = cell_text
            
            processed_table['rows'].append(row_data)
            processed_table['structured_data'].append(row_dict)
        
        #    (RAG)
        processed_table['formatted_text'] = self._format_table_as_text(
            processed_table['headers'],
            processed_table['rows']
        )
        
        return processed_table
    
    def _process_paragraph(self, paragraph) -> Dict[str, Any]:
        """ """
        text = paragraph.text.strip()
        if not text:
            return None
        
        #  
        cleaned_text = self._clean_text(text)
        
        #   
        structure_info = {
            'original': text,
            'cleaned': cleaned_text,
            'style': paragraph.style.name if paragraph.style else None,
            'is_heading': 'Heading' in (paragraph.style.name or ''),
            'has_numbering': self._has_numbering(text),
            'law_references': self._extract_law_references(text)
        }
        
        return structure_info
    
    def _clean_text(self, text: str) -> str:
        """ """
        if not text:
            return ''
        
        #  
        text = text.strip()
        
        #   
        text = re.sub(self.cleaning_patterns['whitespace'], ' ', text)
        
        #   
        text = re.sub(self.cleaning_patterns['repeated_dots'], '...', text)
        
        #    (   )
        # text = re.sub(self.cleaning_patterns['special_chars'], '', text)
        
        return text
    
    def _format_table_as_text(self, headers: List[str], rows: List[List[str]]) -> str:
        """   """
        formatted_lines = []
        
        #   
        if headers:
            for row in rows:
                row_text = []
                for i, (header, cell) in enumerate(zip(headers, row)):
                    if header and cell:
                        #     
                        if '' in header:
                            row_text.append(f"[{header}: {cell}]")
                        elif '' in header or '' in header:
                            row_text.append(f"{header}: {cell}")
                        elif '' in header:
                            row_text.append(f"- {header}: {cell}")
                        else:
                            row_text.append(f"{header}: {cell}")
                
                formatted_lines.append(' '.join(row_text))
        else:
            #   
            for row in rows:
                formatted_lines.append(' | '.join(row))
        
        return '\n'.join(formatted_lines)
    
    def _has_numbering(self, text: str) -> bool:
        """   """
        numbering_patterns = [
            r'^\d+\.',
            r'^\d+\)',
            r'^[-]\.',
            r'^[-]\.',
            r'^\d+',
            r'^\d+'
        ]
        
        for pattern in numbering_patterns:
            if re.match(pattern, text.strip()):
                return True
        return False
    
    def _extract_law_references(self, text: str) -> List[str]:
        """  """
        references = []
        
        #  
        law_numbers = re.findall(r'\s*?\d+', text)
        references.extend(law_numbers)
        
        #  
        articles = re.findall(r'\d+(?:\s*\d+)?', text)
        references.extend(articles)
        
        # /
        regulations = re.findall(r'\s*?\d+|\s*?\d+', text)
        references.extend(regulations)
        
        return references
    
    def save_processed_data(self, processed_data: Dict, output_path: str):
        """  """
        output_path = Path(output_path)
        
        #   
        with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
            for item in processed_data['structured_content']:
                if item['type'] == 'table':
                    f.write("\n[TABLE]\n")
                    f.write(item['content']['formatted_text'])
                    f.write("\n[/TABLE]\n")
                elif item['type'] == 'text':
                    f.write(item['content']['cleaned'])
                    f.write("\n")
        
        #   JSON 
        import json
        json_path = output_path.with_suffix('.json')
        
        # DataFrame dict  JSON   
        json_data = {
            'tables': [
                {
                    'headers': t['headers'],
                    'rows': t['rows'],
                    'formatted_text': t['formatted_text']
                } for t in processed_data['tables']
            ],
            'paragraphs': [
                {
                    'cleaned': p['cleaned'],
                    'style': p['style'],
                    'is_heading': p['is_heading']
                } for p in processed_data['paragraphs']
            ]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Processed data saved to {output_path}")
    
    def print_preprocessing_summary(self, processed_data: Dict):
        """   """
        print("\n" + "="*50)
        print("  ")
        print("="*50)
        print(f" : {len(processed_data['tables'])}")
        print(f" : {len(processed_data['paragraphs'])}")
        
        #   
        if processed_data['tables']:
            print("\n   :")
            table = processed_data['tables'][0]
            print(f"  : {table['headers']}")
            if table['rows']:
                print(f"    : {table['rows'][0]}")
        
        #   
        if processed_data['paragraphs']:
            print("\n   :")
            para = processed_data['paragraphs'][0]
            print(f"  {para['cleaned'][:100]}...")
        
        print("="*50)
