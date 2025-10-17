# api/guardrails.py
import re
from typing import Dict, List

def _has_bootstrap_link(html: str) -> bool:
    return bool(re.search(r'<link[^>]+href=["\'][^"\']*bootstrap[^"\']*["\']', html, re.I))

def _has_selector(html: str, selector_id: str) -> bool:
    sid = selector_id.lstrip("#")
    return bool(re.search(rf'id=["\']{re.escape(sid)}["\']', html, re.I))

def require_highlight_if_checked(files: Dict[str, str], checks: List[str]) -> None:
    html = files.get("index.html", "")
    js = files.get("app.js", "")
    need = any("highlight.js" in c.lower() for c in checks)
    if need and ("highlight.js" not in html and "highlight.js" not in js):
        raise RuntimeError("highlight.js required by checks but not included")

def require_title_if_checked(files: Dict[str, str], checks: List[str]) -> None:
    html = files.get("index.html", "")
    js = files.get("app.js", "")
    needs_title = any("document.title" in c for c in checks)
    if needs_title and ("<title>" not in html and "document.title" not in js):
        raise RuntimeError("title missing but referenced in checks")

def require_selector_if_mentioned(files: Dict[str, str], checks: List[str], seed: str) -> None:
    """
    Expand ${seed} in checks, extract any #ids mentioned, and ensure those ids exist in index.html.
    """
    html = files.get("index.html", "")
    realized_checks = [c.replace("${seed}", seed) for c in checks]
    ids = set(re.findall(r"#[-\w]+", " ".join(realized_checks)))
    for sel in ids:
        if sel == "#":
            continue
        if not _has_selector(html, sel):
            raise RuntimeError(f"selector {sel} missing")
