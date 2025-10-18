====================================================================================================
COMPREHENSIVE METADATA ANALYSIS REPORT
Chunked JSON Files vs Database Schema Comparison
====================================================================================================

====================================================================================================
1. EXACT STATISTICS
====================================================================================================

Total Files Analyzed: 28
Total Chunks: 1,700

Chunks by Category:
--------------------------------------------------------------------------------
  1_공통                :   621 (36.53%)
  2_임대차               :   301 (17.71%)
  3_공급                :   518 (30.47%)
  4_기타                :   260 (15.29%)

Chunks by Document Type:
--------------------------------------------------------------------------------
  기타                  :    23 ( 1.35%)
  대법원규칙               :   225 (13.24%)
  법률                  :   666 (39.18%)
  시행규칙                :   268 (15.76%)
  시행령                 :   426 (25.06%)
  용어집                 :    92 ( 5.41%)

Glossary Chunks by Section:
--------------------------------------------------------------------------------
  건축 용어                         :  10
  그 외 부동산 기초 용어                 :  13
  매매 용어                         :  13
  부동산 대출 관련 용어                  :   5
  신조어 및 줄임말                     :  15
  임대차 용어                        :   9
  재개발 및 재건축                     :  18
  청약 용어                         :   9

Glossary Chunks by Term Category:
--------------------------------------------------------------------------------
  건축                  :  10
  기초용어                :  13
  대출금융                :   5
  매매거래                :  13
  신조어                 :  15
  임대차                 :   9
  재개발재건축              :  18
  청약분양                :   9

====================================================================================================
2. ALL UNIQUE METADATA FIELDS
====================================================================================================

Total Unique Fields: 67
Law-specific Fields: 57
Glossary-specific Fields: 11

Law Chunks Metadata Fields:
--------------------------------------------------------------------------------
  abbreviation                   [str            ] Ex: 
  amendment_count                [int            ] Ex: 2 | 6
  appendix_info                  [str            ] Ex: 부칙 <제1135호,2022. 7. 15.> | 부칙 <제1294호,2023. 12. 29.>
  appendix_references            [list           ] Ex: 
  article_number                 [str            ] Ex: 제67조의3 | 제2조의2
  article_title                  [str            ] Ex: 주택임대차분쟁조정위원회의 분쟁조정 대상에 관한 적용례 | 비주거용 표준부동산가격의 공시사항
  article_type                   [str            ] Ex: 벌칙 | 공시
  chapter                        [str            ] Ex:  | 제5장 이의
  chapter_title                  [str            ] Ex: 공동주택관리 분쟁조정 | 공동주택의 전문관리
  civil_execution_references     [list           ] Ex: 
  decree_number                  [str            ] Ex: 제35161호 | 제34007호
  decree_references              [list           ] Ex: 
  decree_title                   [str            ] Ex: 민간임대주택에 관한 특별법 시행령 ( 약칭: 민간임대주택법 시행령 | 공동주택관리법 시행령
  deletion_date                  [str            ] Ex: 2025. 3. 12. | 2014. 7. 29.
  enforcement_date               [str            ] Ex: 2025. 1. 1. | 2025. 1. 31.
  env_rule_number                [str            ] Ex: 제1019호
  form_references                [list           ] Ex: 
  has_amendments                 [bool           ] Ex: True
  has_appendix_reference         [bool           ] Ex: True
  has_decree_reference           [bool           ] Ex: True
  has_formula                    [bool           ] Ex: True
  has_key_terms                  [bool           ] Ex: True
  has_ministry_rule_reference    [bool           ] Ex: True
  has_penalty                    [bool           ] Ex: True
  has_rule_reference             [bool           ] Ex: True
  in_appendix                    [bool           ] Ex: True
  is_appraisal_related           [bool           ] Ex: True
  is_committee_related           [bool           ] Ex: True
  is_court_rule                  [bool           ] Ex: True
  is_delegation                  [bool           ] Ex: True
  is_deleted                     [bool           ] Ex: True | False
  is_form_related                [bool           ] Ex: True
  is_mediation_related           [bool           ] Ex: True
  is_moved                       [bool           ] Ex: False
  is_noise_related               [bool           ] Ex: True
  is_penalty_related             [bool           ] Ex: True
  is_pilot_program               [bool           ] Ex: True
  is_price_disclosure_related    [bool           ] Ex: True
  is_pricing_related             [bool           ] Ex: True
  is_regulatory_review           [bool           ] Ex: True
  is_series_article              [bool           ] Ex: True
  is_tenant_protection           [bool           ] Ex: True
  item_count                     [int            ] Ex: 2 | 6
  law_article_references         [list           ] Ex: 
  law_number                     [str            ] Ex: 제20385호 | 제20435호
  law_references                 [list           ] Ex: 
  law_title                      [str            ] Ex: 부동산등기법 | 민간임대주택에 관한 특별법
  newly_established              [str            ] Ex: 2019. 8. 20. | 2014. 1. 28.
  other_law_references           [list           ] Ex: 
  price_disclosure_target        [str            ] Ex: 토지 | 비주거용부동산
  rule_number                    [str            ] Ex: 제1118호 | 제1349호
  rule_title                     [str            ] Ex: 공인중개사법 시행규칙 | 부동산 거래신고 등에 관한 법률 시행규칙 ( 약칭: 부동산거래신고법 시행규칙
  section                        [str            ] Ex:  | 임대차 용어
  section_title                  [str            ] Ex: 사업계획의 승인 등 | 주택의 건설
  series_group                   [str            ] Ex: 제3조
  special_enforcement_date       [str            ] Ex: 2023. 10. 19. | 2026. 2. 15.
  table_references               [list           ] Ex: 

Glossary Chunks Metadata Fields:
--------------------------------------------------------------------------------
  definition_length              [int            ] Ex: 47 | 34
  document_type                  [str            ] Ex: glossary
  glossary_title                 [str            ] Ex: 부동산 용어 95가지
  is_abbreviation                [bool           ] Ex: True
  is_financial                   [bool           ] Ex: True
  is_legal_term                  [bool           ] Ex: True
  is_tax_related                 [bool           ] Ex: True
  section                        [str            ] Ex:  | 임대차 용어
  term_category                  [str            ] Ex: 재개발재건축 | 청약분양
  term_name                      [str            ] Ex: 물딱지 | 임대인
  term_number                    [int            ] Ex: 18 | 2

====================================================================================================
3. DATABASE SCHEMA COMPARISON
====================================================================================================

A. Fields in CHUNKS but MISSING in SCHEMA:
--------------------------------------------------------------------------------
  abbreviation                        [str            ] (appears 1 unique values)
  amendment_count                     [int            ] (appears 7 unique values)
  appendix_info                       [str            ] (appears 10 unique values)
  appendix_references                 [list           ] (appears 0 unique values)
  article_type                        [str            ] (appears 5 unique values)
  chapter_title                       [str            ] (appears 15 unique values)
  civil_execution_references          [list           ] (appears 0 unique values)
  decree_number                       [str            ] (appears 7 unique values)
  decree_references                   [list           ] (appears 0 unique values)
  decree_title                        [str            ] (appears 7 unique values)
  definition_length                   [int            ] (appears 59 unique values)
  deletion_date                       [str            ] (appears 10 unique values)
  document_type                       [str            ] (appears 1 unique values)
  env_rule_number                     [str            ] (appears 1 unique values)
  form_references                     [list           ] (appears 0 unique values)
  glossary_title                      [str            ] (appears 1 unique values)
  has_amendments                      [bool           ] (appears 1 unique values)
  has_appendix_reference              [bool           ] (appears 1 unique values)
  has_decree_reference                [bool           ] (appears 1 unique values)
  has_formula                         [bool           ] (appears 1 unique values)
  has_key_terms                       [bool           ] (appears 1 unique values)
  has_ministry_rule_reference         [bool           ] (appears 1 unique values)
  has_penalty                         [bool           ] (appears 1 unique values)
  has_rule_reference                  [bool           ] (appears 1 unique values)
  in_appendix                         [bool           ] (appears 1 unique values)
  is_abbreviation                     [bool           ] (appears 1 unique values)
  is_appraisal_related                [bool           ] (appears 1 unique values)
  is_committee_related                [bool           ] (appears 1 unique values)
  is_court_rule                       [bool           ] (appears 1 unique values)
  is_financial                        [bool           ] (appears 1 unique values)
  is_form_related                     [bool           ] (appears 1 unique values)
  is_legal_term                       [bool           ] (appears 1 unique values)
  is_mediation_related                [bool           ] (appears 1 unique values)
  is_moved                            [bool           ] (appears 1 unique values)
  is_noise_related                    [bool           ] (appears 1 unique values)
  is_pilot_program                    [bool           ] (appears 1 unique values)
  is_price_disclosure_related         [bool           ] (appears 1 unique values)
  is_pricing_related                  [bool           ] (appears 1 unique values)
  is_regulatory_review                [bool           ] (appears 1 unique values)
  is_series_article                   [bool           ] (appears 1 unique values)
  item_count                          [int            ] (appears 7 unique values)
  law_article_references              [list           ] (appears 0 unique values)
  law_number                          [str            ] (appears 9 unique values)
  law_references                      [list           ] (appears 0 unique values)
  law_title                           [str            ] (appears 9 unique values)
  newly_established                   [str            ] (appears 5 unique values)
  other_law_references                [list           ] (appears 0 unique values)
  price_disclosure_target             [str            ] (appears 4 unique values)
  rule_number                         [str            ] (appears 11 unique values)
  rule_title                          [str            ] (appears 11 unique values)
  section_title                       [str            ] (appears 14 unique values)
  series_group                        [str            ] (appears 1 unique values)
  special_enforcement_date            [str            ] (appears 2 unique values)
  table_references                    [list           ] (appears 0 unique values)
  term_category                       [str            ] (appears 8 unique values)
  term_name                           [str            ] (appears 92 unique values)
  term_number                         [int            ] (appears 18 unique values)

B. Fields in SCHEMA but MISSING in CHUNKS:
--------------------------------------------------------------------------------
  category                            (likely computed or derived)
  chunk_ids                           (likely computed or derived)
  doc_type                            (likely computed or derived)
  last_article                        (likely computed or derived)
  metadata_json                       (likely computed or derived)
  number                              (likely computed or derived)
  source_file                         (likely computed or derived)
  title                               (likely computed or derived)
  total_articles                      (likely computed or derived)

C. Law-specific Fields MISSING in SCHEMA:
--------------------------------------------------------------------------------
  abbreviation                        [str            ]
  amendment_count                     [int            ]
  appendix_info                       [str            ]
  appendix_references                 [list           ]
  article_type                        [str            ]
  chapter_title                       [str            ]
  civil_execution_references          [list           ]
  decree_number                       [str            ]
  decree_references                   [list           ]
  decree_title                        [str            ]
  deletion_date                       [str            ]
  env_rule_number                     [str            ]
  form_references                     [list           ]
  has_amendments                      [bool           ]
  has_appendix_reference              [bool           ]
  has_decree_reference                [bool           ]
  has_formula                         [bool           ]
  has_key_terms                       [bool           ]
  has_ministry_rule_reference         [bool           ]
  has_penalty                         [bool           ]
  has_rule_reference                  [bool           ]
  in_appendix                         [bool           ]
  is_appraisal_related                [bool           ]
  is_committee_related                [bool           ]
  is_court_rule                       [bool           ]
  is_form_related                     [bool           ]
  is_mediation_related                [bool           ]
  is_moved                            [bool           ]
  is_noise_related                    [bool           ]
  is_pilot_program                    [bool           ]
  is_price_disclosure_related         [bool           ]
  is_pricing_related                  [bool           ]
  is_regulatory_review                [bool           ]
  is_series_article                   [bool           ]
  item_count                          [int            ]
  law_article_references              [list           ]
  law_number                          [str            ]
  law_references                      [list           ]
  law_title                           [str            ]
  newly_established                   [str            ]
  other_law_references                [list           ]
  price_disclosure_target             [str            ]
  rule_number                         [str            ]
  rule_title                          [str            ]
  section_title                       [str            ]
  series_group                        [str            ]
  special_enforcement_date            [str            ]
  table_references                    [list           ]

D. Glossary-specific Fields MISSING in SCHEMA:
--------------------------------------------------------------------------------
  definition_length                   [int            ]
  document_type                       [str            ]
  glossary_title                      [str            ]
  is_abbreviation                     [bool           ]
  is_financial                        [bool           ]
  is_legal_term                       [bool           ]
  term_category                       [str            ]
  term_name                           [str            ]
  term_number                         [int            ]

====================================================================================================
4. SPECIAL FLAGS AND CATEGORIZATION
====================================================================================================

Boolean Flags Usage (is_* fields):
--------------------------------------------------------------------------------
  is_abbreviation                    :    15 chunks ( 0.88%)
  is_appraisal_related               :     9 chunks ( 0.53%)
  is_committee_related               :     2 chunks ( 0.12%)
  is_court_rule                      :    27 chunks ( 1.59%)
  is_delegation                      :   156 chunks ( 9.18%)
  is_deleted                         :    16 chunks ( 0.94%)
  is_financial                       :     4 chunks ( 0.24%)
  is_form_related                    :    13 chunks ( 0.76%)
  is_legal_term                      :    26 chunks ( 1.53%)
  is_mediation_related               :    17 chunks ( 1.00%)
  is_noise_related                   :     2 chunks ( 0.12%)
  is_penalty_related                 :     1 chunks ( 0.06%)
  is_pilot_program                   :     1 chunks ( 0.06%)
  is_price_disclosure_related        :    90 chunks ( 5.29%)
  is_pricing_related                 :     3 chunks ( 0.18%)
  is_regulatory_review               :     3 chunks ( 0.18%)
  is_series_article                  :     6 chunks ( 0.35%)
  is_tax_related                     :     7 chunks ( 0.41%)
  is_tenant_protection               :    28 chunks ( 1.65%)

Flag Generation Analysis:
--------------------------------------------------------------------------------
  These flags appear to be EXPLICITLY SET in chunk metadata:
    - is_deleted (deletion_date provided)
    - is_tenant_protection (explicitly set)
    - is_tax_related (explicitly set)
    - is_legal_term (explicitly set)
    - is_financial (explicitly set)
    - is_abbreviation (explicitly set)
    - is_delegation (likely auto-detected)
    - is_penalty_related (likely auto-detected)
    - is_series_article (explicitly set with series_group)

====================================================================================================
5. COMPLETE METADATA FIELD MAPPING
====================================================================================================

Chunk Field → Database Field Mapping:
--------------------------------------------------------------------------------
  law_title                 → laws.title                     (Direct mapping)
  law_number                → laws.number                    (Direct mapping)
  enforcement_date          → laws.enforcement_date          (Direct mapping)
  doc_type                  → laws.doc_type                  (Derived from filename/path)
  category                  → laws.category                  (Derived from folder path)
  article_number            → articles.article_number        (Direct mapping)
  article_title             → articles.article_title         (Direct mapping)
  chapter                   → articles.chapter               (Direct mapping)
  section                   → articles.section               (Direct mapping (glossary))
  is_deleted                → articles.is_deleted            (Direct mapping (boolean))
  deletion_date             → metadata_json                  (Stored in JSON)
  is_tenant_protection      → articles.is_tenant_protection  (Direct mapping)
  is_tax_related            → articles.is_tax_related        (Direct mapping)
  is_delegation             → articles.is_delegation         (Direct mapping)
  is_penalty_related        → articles.is_penalty_related    (Direct mapping)
  has_amendments            → metadata_json                  (Stored in JSON)
  amendment_count           → metadata_json                  (Stored in JSON)
  newly_established         → metadata_json                  (Stored in JSON)
  is_series_article         → metadata_json                  (Stored in JSON)
  series_group              → metadata_json                  (Stored in JSON)
  abbreviation              → metadata_json                  (Stored in JSON)
  glossary_title            → laws.title                     (For glossary entries)
  term_number               → articles.article_number        (For glossary entries)
  term_name                 → articles.article_title         (For glossary entries)
  term_category             → metadata_json                  (Stored in JSON)
  is_legal_term             → metadata_json                  (Stored in JSON)
  is_financial              → metadata_json                  (Stored in JSON)
  is_abbreviation           → metadata_json                  (Stored in JSON)
  definition_length         → metadata_json                  (Stored in JSON)
  document_type             → laws.doc_type                  (For glossary)

====================================================================================================
6. RECOMMENDATIONS FOR SCHEMA UPDATES
====================================================================================================

A. No Schema Changes Required:
--------------------------------------------------------------------------------
  ✓ Current schema can handle all chunk metadata
  ✓ Most fields map directly to laws/articles tables
  ✓ Additional metadata stored in articles.metadata_json

B. Glossary-Specific Considerations:
--------------------------------------------------------------------------------
  • Glossary entries use same schema as law articles
  • glossary_title → laws.title
  • term_number → articles.article_number
  • term_name → articles.article_title
  • section → articles.section
  • term_category, is_financial, etc. → articles.metadata_json

C. Optional Schema Enhancements (if needed):
--------------------------------------------------------------------------------
  1. Add laws.abbreviation column (currently in metadata_json)
  2. Add articles.is_series_article column (currently in metadata_json)
  3. Add articles.series_group column (currently in metadata_json)
  4. Add articles.has_amendments column (currently in metadata_json)
  5. Add articles.amendment_count column (currently in metadata_json)

D. Data Type Verification:
--------------------------------------------------------------------------------
  ✓ All boolean flags (is_*) are correctly typed
  ✓ Dates are stored as strings (TEXT) - compatible
  ✓ Numbers (law_number, term_number) stored as TEXT - correct
  ✓ No data type mismatches detected

====================================================================================================
SUMMARY
====================================================================================================

Total Chunks Analyzed: 1,700
Total Files: 28
Unique Metadata Fields: 67
Fields Missing in Schema: 57
Fields in Schema but not Chunks: 9

CONCLUSION:
  ✓ Current database schema is SUFFICIENT for all chunk metadata
  ✓ No critical fields are missing from the schema
  ✓ All chunk data can be stored using existing structure
  ✓ metadata_json field provides flexibility for additional fields

====================================================================================================