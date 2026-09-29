"""Optional LLM phrasing layer (OpenAI-compatible, e.g. Ollama at http://localhost:11434/v1).

The verdict, numbers and evidence ALWAYS come from the rule engine + data layer. The LLM may only
re-phrase the already-composed answer; if it fails, the template answer is returned unchanged.
"""
import httpx

from .config import settings

_LANG = {"en": "English", "hi": "Hindi", "gu": "Gujarati", "ta": "Tamil"}


def enabled() -> bool:
    return bool(settings.llm_base_url and settings.llm_model)


async def rephrase(answer: str, lang: str, mode: str) -> str | None:
    if not enabled():
        return None
    style = "very simple words for a fisherman" if mode == "simple" else "concise technical wording for a coastal officer"
    prompt = (f"Rewrite the following marine advisory in {_LANG.get(lang, 'English')} using {style}. "
              "Keep every number, unit, place name and the verdict exactly as given. Do NOT add facts, numbers, "
              "recommendations or reassurance that are not in the text. Output only the rewritten text.\n\n" + answer)
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{settings.llm_base_url}/chat/completions", headers=headers,
                             json={"model": settings.llm_model, "temperature": 0.1,
                                   "messages": [{"role": "user", "content": prompt}]})
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            return text or None
    except Exception:
        return None
