import hashlib
from typing import Dict
from .models import TaskRequest, BuildResult
from .data_uri import decode_data_uri
from .gh_api import create_and_push_with_gh
from .llm import synthesize_app, generate_readme_via_llm
from .guardrails import (
    require_highlight_if_checked,
    require_title_if_checked,
    require_selector_if_mentioned
)

def _attachment_map(req: TaskRequest) -> Dict[str, bytes]:
    out = {}
    for a in req.attachments:
        _, data = decode_data_uri(a.url)
        out[a.name] = data
    return out

def generate_app_repo(req: TaskRequest) -> BuildResult:
    # Generate seed based on email and nonce (used in element IDs etc.)
    seed = hashlib.sha1(f"{req.email}|{req.nonce}".encode()).hexdigest()[:8]
    attachments = _attachment_map(req)
    extra_vars = {"seed": seed}

    # Generate minimal app using LLM
    files = synthesize_app(req.brief, req.checks, seed, attachments, extra_vars)

    # Add attachments as raw text (if UTF-8)
    for name, data in attachments.items():
        try:
            files[name] = data.decode("utf-8")
        except UnicodeDecodeError:
            files[name] = ""

    # Guardrails: check that generated code includes required elements
    require_highlight_if_checked(files, req.checks)
    require_title_if_checked(files, req.checks)
    require_selector_if_mentioned(files, req.checks, seed)  # ✅ FIX: pass seed here

    # Add LLM-generated README
    files["README.md"] = generate_readme_via_llm(req.brief, req.checks)

    # Create GitHub repo + push + enable Pages
    repo_name = req.task.replace(" ", "-")
    res = create_and_push_with_gh(repo_name=repo_name, files=files)

    return BuildResult(
        repo_url=res.repo_url,
        pages_url=res.pages_url,
        commit_sha=res.commit_sha
    )
