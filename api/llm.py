from typing import List, Dict, Tuple
import re
from .settings import settings

try:
    # modern OpenAI client (works with AI Pipe base_url)
    from openai import OpenAI
except ImportError:
    OpenAI = None

# ---------- client ----------
def _client():
    if OpenAI is None:
        raise RuntimeError("openai package is not installed")
    if not settings.OPENAI_API_KEY or not settings.OPENAI_BASE_URL:
        raise RuntimeError("OPENAI_API_KEY/OPENAI_BASE_URL not set")
    return OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)

# ---------- LLM README ----------
def generate_readme_via_llm(brief: str, checks: List[str], repo_url: str = "", pages_url: str = "") -> str:
    client = _client()
    req = (
        "Write a professional README.md for a static web app.\n"
        "Include these sections exactly and in this order:\n"
        "1) Title\n2) Summary\n3) Setup (Local)\n4) Usage\n5) Code Explanation\n6) Deployment (GitHub Pages)\n7) License (MIT)\n\n"
        f"Brief:\n{brief}\n\nEvaluation checks:\n- " + "\n- ".join(checks) + "\n\n"
        + (f"Repository URL: {repo_url}\n" if repo_url else "")
        + (f"Live URL: {pages_url}\n" if pages_url else "")
        + "Keep it concise and actionable."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",  # or "openai/gpt-4.1-nano" if using OpenRouter naming
        messages=[
            {"role": "system", "content": "You write concise, high-quality GitHub READMEs."},
            {"role": "user", "content": req},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

# ---------- synthesis ----------
_FENCE_RE = re.compile(r"<<(INDEX_HTML|APP_JS)>>\s*([\s\S]*?)\s*<</\1>>", re.IGNORECASE)

def _extract_blocks(text: str) -> Tuple[str, str]:
    html, js = "", ""
    for kind, body in _FENCE_RE.findall(text):
        if kind.upper() == "INDEX_HTML": html = body.strip()
        elif kind.upper() == "APP_JS":   js = body.strip()
    return html, js

def synthesize_app(brief: str, checks: List[str], seed: str, attachments: Dict[str, bytes], extra_vars: Dict[str, str]) -> Dict[str, str]:
    client = _client()
    attach_list = list(attachments.keys())
    checks_text = "\n".join(f"- {c}" for c in checks)
    var_lines = "\n".join(f"- {k}: {v}" for k, v in (extra_vars or {}).items()) or "- (no extra vars)"

    prompt = f"""
You are generating a minimal static web app with exactly two files: index.html and app.js.

Rules:
- Satisfy the brief and all checks.
- Required selectors (e.g. #total-sales, #github-created-at) must exist and be updated by JS.
- If a title is required, set document.title.
- If Bootstrap is required, include a <link> whose href contains 'bootstrap'.
- If 'highlight.js' is required, include its script and call highlightElement on code blocks.
- If attachments are referenced, use fetch('<filename>') where filename is one of: {attach_list or "[]"}.
- Use vanilla JS and CDN links (Bootstrap 5 via jsDelivr, marked, highlight.js).
- Keep total output < 200 lines.

Seed/context variables:
- seed: {seed}
{var_lines}

Brief:
{brief}

Checks to satisfy:
{checks_text}

Output FORMAT (strict):
<<INDEX_HTML>>
[the full HTML file here]
<</INDEX_HTML>>

<<APP_JS>>
[the full JS file here]
<</APP_JS>>
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",  # or "openai/gpt-4.1-nano"
        messages=[
            {"role": "system", "content": "Generate only the two code blocks requested; no extra prose."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.15,
    )
    content = resp.choices[0].message.content
    html, js = _extract_blocks(content)
    if not html or not js:
        raise RuntimeError("LLM did not return required code blocks")
    return {"index.html": html, "app.js": js}
