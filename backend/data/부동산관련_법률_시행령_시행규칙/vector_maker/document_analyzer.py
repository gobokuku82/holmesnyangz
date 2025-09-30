"""
   
-   
-   
-  
"""
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import docx
from docx.table import Table
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DocumentStructure:
    """  """
    doc_type: str  #   (table, mixed, text)
    has_tables: bool
    table_count: int
    sections: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    hierarchy: Dict[str, Any]

class DocumentAnalyzer:
    """  """
    
    def __init__(self):
        self.structure_patterns = {
            '': r'|||',
            '': r'||||',
            '': r'|||\s*',
            '': r'\d+|\d+|\d+',
            '': r'\d{4}\s*\d{1,2}\s*\d{1,2}|\d{8}',
        }
    
    def analyze(self, file_path: str) -> DocumentStructure:
        """   """
        file_path = Path(file_path)
        
        if file_path.suffix.lower() in ['.docx', '.doc']:
            return self._analyze_word(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    def _analyze_word(self, file_path: Path) -> DocumentStructure:
        """Word   """
        doc = docx.Document(str(file_path))
        
        #  
        tables_info = self._analyze_tables(doc.tables)
        
        #   
        text_structure = self._analyze_text_structure(doc.paragraphs)
        
        #  
        metadata = self._extract_metadata(doc)
        
        #   
        doc_type = self._determine_doc_type(tables_info, text_structure)
        
        return DocumentStructure(
            doc_type=doc_type,
            has_tables=len(tables_info) > 0,
            table_count=len(tables_info),
            sections=self._merge_sections(tables_info, text_structure),
            metadata=metadata,
            hierarchy=self._build_hierarchy(tables_info, text_structure)
        )
    
    def _analyze_tables(self, tables: List[Table]) -> List[Dict[str, Any]]:
        """  """
        tables_info = []
        
        for idx, table in enumerate(tables):
            table_info = {
                'type': 'table',
                'index': idx,
                'rows': len(table.rows),
                'cols': len(table.columns),
                'headers': [],
                'content_preview': [],
                'structure_type': None  # legal_table, comparison_table, etc.
            }
            
            #  
            if len(table.rows) > 0:
                headers = []
                for cell in table.rows[0].cells:
                    header_text = cell.text.strip()
                    headers.append(header_text)
                    
                    #     
                    if any(re.search(pattern, header_text) 
                          for pattern in self.structure_patterns.values()):
                        table_info['structure_type'] = 'legal_table'
                
                table_info['headers'] = headers
            
            #   ( 3)
            for row_idx, row in enumerate(table.rows[1:4]):
                row_content = [cell.text.strip()[:50] for cell in row.cells]
                table_info['content_preview'].append(row_content)
            
            tables_info.append(table_info)
        
        return tables_info
    
    def _analyze_text_structure(self, paragraphs) -> List[Dict[str, Any]]:
        """  """
        text_structure = []
        current_section = None
        
        for para in paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            # / 
            if para.style.name and 'Heading' in para.style.name:
                if current_section:
                    text_structure.append(current_section)
                current_section = {
                    'type': 'section',
                    'title': text,
                    'level': int(para.style.name[-1]) if para.style.name[-1].isdigit() else 0,
                    'content': []
                }
            elif current_section:
                current_section['content'].append(text)
            else:
                text_structure.append({
                    'type': 'paragraph',
                    'content': text
                })
        
        if current_section:
            text_structure.append(current_section)
        
        return text_structure
    
    def _extract_metadata(self, doc) -> Dict[str, Any]:
        """ """
        metadata = {}
        
        #  
        if doc.core_properties:
            metadata['title'] = doc.core_properties.title or ''
            metadata['author'] = doc.core_properties.author or ''
            metadata['created'] = str(doc.core_properties.created) if doc.core_properties.created else ''
            metadata['modified'] = str(doc.core_properties.modified) if doc.core_properties.modified else ''
        
        #     ()
        all_text = '\n'.join([p.text for p in doc.paragraphs[:10]])  #  10 
        
        #   
        law_numbers = re.findall(r'\d+|\s*\d+', all_text)
        if law_numbers:
            metadata['law_numbers'] = law_numbers
        
        #  
        dates = re.findall(r'\d{4}\s*\d{1,2}\s*\d{1,2}', all_text)
        if dates:
            metadata['dates'] = dates
        
        return metadata
    
    def _determine_doc_type(self, tables_info: List, text_structure: List) -> str:
        """  """
        if not tables_info:
            return 'text'
        elif len(tables_info) > len(text_structure):
            return 'table_heavy'
        else:
            return 'mixed'
    
    def _merge_sections(self, tables_info: List, text_structure: List) -> List[Dict]:
        """   """
        #   -      
        sections = []
        sections.extend(tables_info)
        sections.extend(text_structure)
        return sections
    
    def _build_hierarchy(self, tables_info: List, text_structure: List) -> Dict:
        """  """
        hierarchy = {
            'root': {
                'tables': [t['index'] for t in tables_info],
                'sections': [s.get('title', 'untitled') for s in text_structure if s['type'] == 'section']
            }
        }
        return hierarchy
    
    def print_structure_summary(self, structure: DocumentStructure):
        """  """
        print("\n" + "="*50)
        print("Document Structure Analysis Result")
        print("="*50)
        print(f" : {structure.doc_type}")
        print(f" : {structure.table_count}")
        
        if structure.has_tables:
            print("\nTable Information:")
            for section in structure.sections:
                if section.get('type') == 'table':
                    print(f"  -  {section['index']}: {section['rows']} x {section['cols']}")
                    print(f"    : {', '.join(section['headers'][:3])}")
        
        if structure.metadata:
            print("\nMetadata:")
            for key, value in structure.metadata.items():
                if value:
                    print(f"  - {key}: {value}")
        
        print("="*50)
