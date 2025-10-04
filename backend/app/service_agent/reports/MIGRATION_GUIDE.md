# LLM Manager Migration Guide

## Overview

This guide explains how to migrate existing agents from direct OpenAI API calls to the centralized `LLMService`.

## Benefits of Migration

- **Consistency**: All LLM calls use the same configuration and retry logic
- **Maintainability**: Prompt templates are centralized and versioned
- **Performance**: Client reuse and prompt caching reduce overhead
- **Monitoring**: Centralized logging and token tracking
- **Error Handling**: Automatic retry with exponential backoff

## Migration Steps

### Step 1: Import LLMService

**Before:**
```python
from openai import OpenAI
from app.service_agent.foundation.config import Config

client = OpenAI(api_key=self.llm_context.api_key)
```

**After:**
```python
from app.service_agent.llm_manager import LLMService

llm_service = LLMService(llm_context=self.llm_context)
```

### Step 2: Create Prompt Template

Create a prompt template file in the appropriate folder:

- `prompts/cognitive/` - For planning, intent analysis, strategy selection
- `prompts/execution/` - For search, analysis, document generation
- `prompts/common/` - For shared prompts (error handling, etc.)

**Example:** `prompts/execution/keyword_extraction.txt`
```
당신은 검색 키워드를 추출하는 전문가입니다.

사용자 질의: {query}
도메인: {domain}

위 질의에서 효과적인 검색을 위한 키워드를 추출하세요.

다음 형식의 JSON으로 응답하세요:
{{
    "primary_keywords": ["핵심키워드1", "핵심키워드2"],
    "secondary_keywords": ["보조키워드1", "보조키워드2"]
}}
```

**Note:** Use `{{` and `}}` for literal braces in JSON format strings.

### Step 3: Replace LLM Calls

**Before:**
```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{
        "role": "system",
        "content": f"사용자 질의: {query}\n\n키워드를 추출하세요..."
    }],
    temperature=0.3,
    max_tokens=500,
    response_format={"type": "json_object"}
)

result = json.loads(response.choices[0].message.content)
```

**After:**
```python
result = llm_service.complete_json(
    prompt_name="keyword_extraction",
    variables={
        "query": query,
        "domain": domain
    }
)
```

### Step 4: Configure Model (Optional)

Add model mapping to `foundation/config.py`:

```python
LLM_DEFAULTS = {
    "models": {
        "keyword_extraction": "gpt-4o-mini",  # Add your prompt here
        ...
    }
}
```

If not specified, defaults to `gpt-4o-mini`.

## API Reference

### LLMService Methods

#### `complete(prompt_name, variables, **kwargs) -> str`
Synchronous LLM call returning text response.

```python
response = llm_service.complete(
    prompt_name="intent_analysis",
    variables={"query": "강남구 전세 시세"},
    temperature=0.5,  # Optional override
    model="gpt-4o"    # Optional override
)
```

#### `complete_json(prompt_name, variables, **kwargs) -> dict`
Synchronous LLM call returning parsed JSON.

```python
result = llm_service.complete_json(
    prompt_name="keyword_extraction",
    variables={"query": query, "domain": "legal"}
)
```

#### `complete_async(prompt_name, variables, **kwargs) -> str`
Async version of `complete()`.

```python
response = await llm_service.complete_async(
    prompt_name="insight_generation",
    variables={"query": query, "search_results": results}
)
```

#### `complete_json_async(prompt_name, variables, **kwargs) -> dict`
Async version of `complete_json()`.

```python
result = await llm_service.complete_json_async(
    prompt_name="plan_generation",
    variables={"query": query, "intent_result": intent}
)
```

### PromptManager Methods

#### `get(prompt_name, variables, category=None) -> str`
Load and render prompt template.

```python
prompt = llm_service.prompt_manager.get(
    prompt_name="intent_analysis",
    variables={"query": "전세 계약은?"},
    category="cognitive"  # Optional, auto-detected if None
)
```

#### `list_prompts(category=None) -> dict`
List available prompts.

```python
prompts = llm_service.prompt_manager.list_prompts()
# Returns: {"cognitive": [...], "execution": [...], "common": [...]}
```

#### `validate(prompt_name, required_variables=None) -> bool`
Validate prompt template.

```python
is_valid = llm_service.prompt_manager.validate(
    prompt_name="intent_analysis",
    required_variables=["query"]
)
```

## Migration Examples

### Example 1: Planning Agent

**Before:**
```python
def _analyze_intent(self, query: str) -> Dict[str, Any]:
    client = OpenAI(api_key=self.llm_context.api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": f"분석할 질의: {query}..."}],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)
```

**After:**
```python
def _analyze_intent(self, query: str) -> Dict[str, Any]:
    return self.llm_service.complete_json(
        prompt_name="intent_analysis",
        variables={"query": query}
    )
```

### Example 2: Search Executor

**Before:**
```python
async def _extract_keywords(self, query: str) -> List[str]:
    client = AsyncOpenAI(api_key=self.llm_context.api_key)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": f"키워드 추출: {query}..."}]
    )

    return response.choices[0].message.content.split(",")
```

**After:**
```python
async def _extract_keywords(self, query: str) -> List[str]:
    result = await self.llm_service.complete_json_async(
        prompt_name="keyword_extraction",
        variables={"query": query, "domain": self.domain}
    )

    return result["primary_keywords"]
```

## Best Practices

1. **Use descriptive prompt names**: `intent_analysis` not `analyze1`
2. **Document required variables**: Add comments listing required variables
3. **Use JSON mode for structured output**: `complete_json()` instead of parsing text
4. **Leverage caching**: Prompt templates are cached automatically
5. **Handle errors gracefully**: LLMService has built-in retry logic
6. **Keep prompts DRY**: Reuse common prompts across agents

## Testing

After migration, test with:

```bash
python app/service_agent/llm_manager/test_llm_manager.py
```

## Rollback Plan

If issues arise, the old code can be restored since:
- Original agent files are unchanged until migration
- LLMService is additive, not destructive
- Config maintains backward compatibility with legacy mappings

## Next Steps

1. ✅ Create prompt templates for your agent
2. ✅ Update agent to use LLMService
3. ✅ Test locally
4. ✅ Monitor token usage in logs
5. ✅ Migrate remaining agents incrementally
