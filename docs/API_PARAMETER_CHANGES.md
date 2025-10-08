# Azure OpenAI API Parameter Changes - max_tokens vs max_completion_tokens

## 🔧 Issue

Starting with newer Azure OpenAI models, the API parameter for limiting output length has changed from `max_tokens` to `max_completion_tokens`.

## 📋 Affected Models

Models that **require** `max_completion_tokens` instead of `max_tokens`:

### GPT-4o Series
- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4o-2024-*` (all variants)

### GPT-4.1 Series
- `gpt-4.1`
- `gpt-4.1-mini`
- `gpt-4.1-nano`

### GPT-5 Series
- `gpt-5`
- `gpt-5-mini`
- `gpt-5-nano`

### o-Series (Reasoning Models)
- `o1-preview`
- `o1-mini`
- `o3`
- `o3-mini`
- `o4-mini`

## ❌ Error Message

If you use the wrong parameter, you'll see:

```
BadRequestError: Error code: 400 - {'error': {'message': "Unsupported parameter: 
'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead.", 
'type': 'invalid_request_error', 'param': 'max_tokens', 'code': 
'unsupported_parameter'}}
```

## ✅ Solution

### For LangChain (AzureChatOpenAI)

**Old Code (causes error with new models):**
```python
from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    openai_api_key=API_KEY,
    azure_endpoint=ENDPOINT,
    deployment_name="gpt-4o-mini",
    api_version=API_VERSION,
    max_tokens=8192,  # ❌ Error with gpt-4o-mini
)
```

**New Code (works with new models):**
```python
from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    openai_api_key=API_KEY,
    azure_endpoint=ENDPOINT,
    deployment_name="gpt-4o-mini",
    api_version=API_VERSION,
    max_completion_tokens=8192,  # ✅ Correct
)
```

### Dynamic Detection Function

Use this helper function to automatically choose the correct parameter:

```python
def _uses_completion_tokens(deployment_name: str | None) -> bool:
    """Check if a model requires max_completion_tokens instead of max_tokens."""
    name = (deployment_name or "").lower()
    return (
        name.startswith('gpt-4o') or 
        name.startswith('gpt-5') or 
        name.startswith('gpt-4.1') or
        name.startswith('o1') or 
        name.startswith('o3') or
        name.startswith('o4')
    )

def _make_llm(deployment_name: str, max_tokens: int = 8192):
    """Create LLM with correct parameter based on model type."""
    if _uses_completion_tokens(deployment_name):
        return AzureChatOpenAI(
            openai_api_key=API_KEY,
            azure_endpoint=ENDPOINT,
            deployment_name=deployment_name,
            api_version=API_VERSION,
            max_completion_tokens=max_tokens,  # New parameter
        )
    else:
        return AzureChatOpenAI(
            openai_api_key=API_KEY,
            azure_endpoint=ENDPOINT,
            deployment_name=deployment_name,
            api_version=API_VERSION,
            max_tokens=max_tokens,  # Old parameter
        )
```

## 📊 Model Compatibility Matrix

| Model Family | Parameter | Status |
|--------------|-----------|--------|
| GPT-3.5 | `max_tokens` | Legacy |
| GPT-4 (base) | `max_tokens` | Legacy |
| GPT-4-Turbo | `max_tokens` | Legacy |
| **GPT-4o** | **`max_completion_tokens`** | ✅ Active |
| **GPT-4.1** | **`max_completion_tokens`** | ✅ Active |
| **GPT-5** | **`max_completion_tokens`** | ✅ Active |
| **o-series** | **`max_completion_tokens`** | ✅ Active |

## 🔍 Why the Change?

The new parameter name `max_completion_tokens` is more explicit about what it controls:
- It limits only the **completion** (output) tokens
- Input tokens are not counted against this limit
- More predictable behavior for users
- Aligns with newer API design patterns

## 📝 Where This Was Fixed

### In this Repository:

1. **`/ui/streamlit_app/app_multimodel.py`**
   - Updated `_make_llm()` function with dynamic detection
   - Affects: gpt-4o-mini, gpt-4.1, gpt-5-mini, gpt-4.1-mini

2. **`/nl2sql_standalone_Langchain/1_nl2sql_main.py`**
   - Updated `_make_llm()` function with dynamic detection
   - Affects: Any deployment configured in `AZURE_OPENAI_DEPLOYMENT_NAME`

3. **`/ui/streamlit_app/app.py`**
   - Inherits fix from `1_nl2sql_main.py` import
   - No direct changes needed

## 🧪 Testing

Test that your fix works:

```python
# This should NOT raise an error with gpt-4o-mini
llm = _make_llm("gpt-4o-mini", max_tokens=2048)
response = llm.invoke("Say hello")
print(response.content)  # Should print: "Hello!" or similar
```

## 📚 References

- [Azure OpenAI API Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [LangChain Azure OpenAI Integration](https://python.langchain.com/docs/integrations/llms/azure_openai)
- [Azure OpenAI Model API Changes](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/reasoning#api-&-feature-support)

## ⚠️ Migration Checklist

If you're updating existing code:

- [ ] Identify all places where `AzureChatOpenAI` is instantiated
- [ ] Check the model/deployment names being used
- [ ] Add dynamic detection function (`_uses_completion_tokens`)
- [ ] Update LLM factory function to use correct parameter
- [ ] Test with actual API calls
- [ ] Update documentation and comments
- [ ] Consider adding this check to CI/CD pipeline

## 🎯 Quick Fix Summary

**Before:**
```python
llm = AzureChatOpenAI(..., max_tokens=8192)
```

**After:**
```python
# For gpt-4o, gpt-4.1, gpt-5, o-series
llm = AzureChatOpenAI(..., max_completion_tokens=8192)

# For older models (gpt-3.5, gpt-4 base)
llm = AzureChatOpenAI(..., max_tokens=8192)
```

**Best Practice (Dynamic):**
```python
def _make_llm(deployment_name, max_tokens=8192):
    param_key = "max_completion_tokens" if is_new_model(deployment_name) else "max_tokens"
    return AzureChatOpenAI(..., **{param_key: max_tokens})
```

---

**Last Updated**: October 8, 2025  
**Applies to**: Azure OpenAI API version 2025-04-01-preview and later
