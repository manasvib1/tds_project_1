import os
import tempfile
import subprocess
import pathlib
import base64
import textwrap
import stat
from typing import Dict
from .models import TaskRequest, BuildResult
from .settings import settings
from .llm import generate_readme_via_llm, synthesize_app
from .notifier import notify_with_backoff
from .guardrails import (
    require_highlight_if_checked,
    require_title_if_checked,
    require_selector_if_mentioned,
)

def _run(cmd: list, cwd=None, env=None):
    print("RUN:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd, env=env)

def push_with_token(repo_path: str, repo_name: str):
    """
    Push the current branch to origin using token via a temporary GIT_ASKPASS helper.
    This avoids interactive prompts in containers.
    """
    token = settings.GITHUB_TOKEN or os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN / GH_TOKEN not set - cannot push")

    username = settings.GITHUB_USERNAME
    if not username:
        raise RuntimeError("GITHUB_USERNAME not set")

    askpass_path = os.path.join(repo_path, "git_askpass.sh")
    askpass_content = textwrap.dedent(f"""\
        #!/usr/bin/env sh
        # Git askpass helper - prints token for git to use as password
        printf '%s' "{token}"
    """)
    with open(askpass_path, "w", encoding="utf-8") as f:
        f.write(askpass_content)

    # make executable
    st = os.stat(askpass_path)
    os.chmod(askpass_path, st.st_mode | stat.S_IEXEC)

    # Ensure remote uses username so git calls askpass for password
    remote_url = f"https://{username}@github.com/{username}/{repo_name}.git"
    _run(["git", "remote", "set-url", "origin", remote_url], cwd=repo_path)

    env = os.environ.copy()
    env["GIT_ASKPASS"] = askpass_path
    env["GIT_TERMINAL_PROMPT"] = "0"

    try:
        # push current branch (assumes branch already set to origin/main)
        _run(["git", "push", "origin", settings.DEFAULT_BRANCH], cwd=repo_path, env=env)
    finally:
        # remove helper
        try:
            os.remove(askpass_path)
        except Exception:
            pass

def update_existing_repo_with_llm(req: TaskRequest) -> BuildResult:
    assert req.round == 2, "This function only supports round 2"

    # Use same repo name as in round 1
    repo_name = req.task.replace(" ", "-")
    username = settings.GITHUB_USERNAME
    repo_url = f"https://github.com/{username}/{repo_name}.git"

    tmp = tempfile.mkdtemp()
    repo_path = pathlib.Path(tmp) / repo_name

    # Clone the repo
    _run(["git", "clone", repo_url, str(repo_path)])
    _run(["git", "checkout", settings.DEFAULT_BRANCH], cwd=repo_path)
    # Ensure local identity for commits (safe, local repo-level config)
    _run(["git", "config", "user.email", "bot@llm-deploy.local"], cwd=repo_path)
    _run(["git", "config", "user.name", settings.GITHUB_USERNAME or "llm-deploy-bot"], cwd=repo_path)

    # Read current files
    index_path = repo_path / "index.html"
    app_path = repo_path / "app.js"

    if not index_path.exists() or not app_path.exists():
        raise RuntimeError("Existing repo does not contain index.html or app.js")

    old_files = {
        "index.html": index_path.read_text(encoding="utf-8"),
        "app.js": app_path.read_text(encoding="utf-8"),
    }

    seed = req.nonce[:8]
    attachments = {}  # Round 2 usually doesn't include new attachments
    extra_vars = {"seed": seed, "round": 2}

    # Ask LLM to modify the existing app
    updated_files = synthesize_app(
        brief=req.brief,
        checks=req.checks,
        seed=seed,
        attachments=attachments,
        extra_vars=extra_vars,
    )

    # Overwrite files
    for name, content in updated_files.items():
        fpath = repo_path / name
        fpath.write_text(content, encoding="utf-8")

    # Rebuild README
    readme = generate_readme_via_llm(req.brief, req.checks, repo_url=repo_url, pages_url=f"https://{username}.github.io/{repo_name}/")
    (repo_path / "README.md").write_text(readme, encoding="utf-8")

    # Guardrails
    require_highlight_if_checked(updated_files, req.checks)
    require_title_if_checked(updated_files, req.checks)
    require_selector_if_mentioned(updated_files, req.checks, seed)

    # Commit and push (use token-safe push helper)
    _run(["git", "add", "."], cwd=repo_path)
    _run(["git", "commit", "-m", "update: round 2 requirements"], cwd=repo_path)

    # Push with token helper to avoid interactive prompts in container
    push_with_token(repo_path=str(repo_path), repo_name=repo_name)

    # Notify
    if req.evaluation_url:
        notify_with_backoff(
            evaluation_url=req.evaluation_url,
            payload={
                "email": req.email,
                "task": req.task,
                "round": req.round,
                "nonce": req.nonce,
                "repo_url": f"https://github.com/{username}/{repo_name}",
                "commit_sha": os.popen(f"git -C {repo_path} rev-parse HEAD").read().strip(),
                "pages_url": f"https://{username}.github.io/{repo_name}/"
            }
        )

    return BuildResult(
        repo_url=f"https://github.com/{username}/{repo_name}",
        pages_url=f"https://{username}.github.io/{repo_name}/",
        commit_sha=os.popen(f"git -C {repo_path} rev-parse HEAD").read().strip()
    )
