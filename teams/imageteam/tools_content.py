"""
Content generation tools — captions, alt text, titles, descriptions.
Always contextual — uses brand memory, platform, audience.
"""

import os
import httpx
from typing import Optional

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LITELLM_URL = os.environ.get("LITELLM_URL", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


async def _generate_text(system: str, prompt: str, model: str = "qwen2.5:7b") -> str:
    if ANTHROPIC_API_KEY:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=ANTHROPIC_API_KEY)
            r = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return r.content[0].text
        except Exception:
            pass

    if LITELLM_URL:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{LITELLM_URL}/chat/completions", json={
                "model": f"ollama/{model}",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1024,
            })
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json={
            "model": model, "system": system, "prompt": prompt, "stream": False,
        })
        if r.status_code == 200:
            return r.json().get("response", "")

    return ""


async def generate_caption(
    image_description: str,
    platform: str = "instagram",
    tone: str = "professional",
    brand_name: str = "",
    target_audience: str = "",
    include_hashtags: bool = True,
    include_emoji: bool = True,
    language: str = "en",
) -> dict:
    """Generate a contextual social media caption."""
    prompt = f"""Generate a {platform} caption for an image described as:
"{image_description}"

Platform: {platform}
Tone: {tone}
Brand: {brand_name or "not specified"}
Audience: {target_audience or "general"}
Language: {language}
Include hashtags: {include_hashtags}
Include emoji: {include_emoji}

Platform guidelines:
- Instagram: up to 2200 chars, 30 hashtags max, line breaks for readability
- Twitter/X: 280 chars max, 2-3 hashtags
- LinkedIn: professional, 1-3 hashtags, thought leadership
- Facebook: conversational, question hooks, no hashtag overload
- TikTok: short, trendy, challenge/trend references
- Pinterest: SEO-focused, descriptive, keyword-rich"""

    caption = await _generate_text(
        "You are an expert social media copywriter. Write engaging, platform-optimized captions.",
        prompt,
    )
    return {"caption": caption, "platform": platform, "tool": "caption_generator"}


async def generate_alt_text(
    image_description: str,
    context: str = "",
    max_length: int = 125,
) -> dict:
    """Generate accessible alt text for an image (WCAG compliant)."""
    prompt = f"""Write alt text for this image: "{image_description}"
Context: {context or "website image"}

Rules:
- Max {max_length} characters
- Describe the image content, not its purpose
- Don't start with "Image of" or "Photo of"
- Include relevant details for screen readers
- Be specific and concise"""

    alt = await _generate_text(
        "You write accessible alt text following WCAG 2.1 guidelines. Be concise and descriptive.",
        prompt,
    )
    return {"alt_text": alt[:max_length], "characters": len(alt[:max_length]), "tool": "alt_text_generator"}


async def generate_seo_metadata(
    image_description: str,
    page_context: str = "",
    brand_name: str = "",
    keywords: list[str] = None,
) -> dict:
    """Generate SEO title, description, and schema.org data for an image."""
    prompt = f"""Generate SEO metadata for an image:
Image: {image_description}
Page context: {page_context or "website"}
Brand: {brand_name or "not specified"}
Target keywords: {', '.join(keywords) if keywords else "auto-detect"}

Return JSON with:
- title: SEO title (50-60 chars)
- description: meta description (150-160 chars)
- alt_text: accessible alt text (125 chars max)
- og_title: Open Graph title
- og_description: Open Graph description
- schema_name: schema.org ImageObject name
- schema_description: schema.org description
- keywords: relevant keywords array"""

    result = await _generate_text(
        "You are an SEO specialist. Return valid JSON only.",
        prompt,
    )

    import json
    try:
        parsed = json.loads(result)
    except:
        parsed = {
            "title": image_description[:60],
            "description": image_description[:160],
            "alt_text": image_description[:125],
        }

    return {**parsed, "tool": "seo_metadata_generator"}


async def generate_multi_platform_content(
    image_description: str,
    platforms: list[str] = None,
    tone: str = "professional",
    brand_name: str = "",
    target_audience: str = "",
) -> dict:
    """Generate captions + metadata for multiple platforms at once."""
    platforms = platforms or ["instagram", "twitter", "linkedin", "facebook"]

    results = {}
    for platform in platforms:
        caption = await generate_caption(
            image_description, platform, tone, brand_name, target_audience,
        )
        results[platform] = caption

    alt = await generate_alt_text(image_description)
    seo = await generate_seo_metadata(image_description, brand_name=brand_name)

    return {
        "captions": results,
        "alt_text": alt,
        "seo": seo,
        "tool": "multi_platform_content",
    }


CONTENT_TOOL_MAP = {
    "generate_caption": generate_caption,
    "generate_alt_text": generate_alt_text,
    "generate_seo_metadata": generate_seo_metadata,
    "generate_multi_platform": generate_multi_platform_content,
}
