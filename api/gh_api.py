import os, subprocess, tempfile, pathlib, time
from .settings import settings

PAGES_WORKFLOW = """name: GitHub Pages
on:
  push:
    branches: [ %BRANCH% ]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: "pages"
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - name: Setup Pages
        uses: actions/configure-pages@v5
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: .
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""

MIT_LICENSE = """MIT License

Copyright (c) %YEAR% %AUTHOR%

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

class RepoResult:
    def __init__(self, repo_url: str, pages_url: str, commit_sha: str):
        self.repo_url = repo_url
        self.pages_url = pages_url
        self.commit_sha = commit_sha

def _run(cmd: list, cwd=None):
    print("RUN:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd)

def create_and_push_with_gh(repo_name: str, files: dict) -> RepoResult:
    username = settings.GITHUB_USERNAME
    assert username, "GITHUB_USERNAME required"

    tmp = tempfile.mkdtemp()
    root = pathlib.Path(tmp) / repo_name
    root.mkdir(parents=True)

    for path, content in files.items():
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    (root / "LICENSE").write_text(
        MIT_LICENSE.replace("%YEAR%", time.strftime("%Y")).replace("%AUTHOR%", username),
        encoding="utf-8",
    )

    workflow = PAGES_WORKFLOW.replace("%BRANCH%", settings.DEFAULT_BRANCH)
    workflow_path = root / ".github" / "workflows" / "pages.yml"
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(workflow, encoding="utf-8")

    _run(["git", "init", "-b", settings.DEFAULT_BRANCH], cwd=root)
    _run(["git", "config", "user.email", "bot@llm-deploy.local"], cwd=root)
    _run(["git", "config", "user.name", username], cwd=root)
    _run(["git", "add", "."], cwd=root)
    _run(["git", "commit", "-m", "init: task scaffold"], cwd=root)

    _run([
        "gh", "repo", "create", f"{username}/{repo_name}",
        "--public", "--source", str(root), "--remote", "origin", "--push"
    ])

    # Auto-enable Pages via REST (safe; ignore failure)
    try:
        _run(["gh","api",f"/repos/{username}/{repo_name}/pages","-X","POST","-F","build_type=workflow"])
    except subprocess.CalledProcessError as e:
        print("WARN: Auto-enable Pages failed; Actions may enable on first deploy:", e)

    repo_url = f"https://github.com/{username}/{repo_name}"
    pages_url = f"https://{username}.github.io/{repo_name}/"
    commit_sha = os.popen(f"git -C {root} rev-parse HEAD").read().strip()
    return RepoResult(repo_url, pages_url, commit_sha)
