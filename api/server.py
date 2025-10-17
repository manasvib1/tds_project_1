from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse
from .models import TaskRequest
from .security import verify_secret
from .generator import generate_app_repo
from .notifier import notify_with_backoff
import pathlib, traceback

app = FastAPI(title="LLM Code Deployment API (Synthesizing)")

# Landing + debug endpoints
@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/docs")

@app.get("/_routes", include_in_schema=False)
async def debug_routes():
    try:
        r = [{"path": rt.path, "name": getattr(rt, "name", "")} for rt in app.routes]
        return JSONResponse(r)
    except Exception:
        return JSONResponse({"error": "listing routes failed", "trace": traceback.format_exc()})

# ---- MAIN ENDPOINT ----
@app.post("/task", response_model=None)
async def receive_task(req: TaskRequest, background_tasks: BackgroundTasks):
    # 1️⃣ Verify secret first
    if not verify_secret(req.secret):
        raise HTTPException(status_code=401, detail="Invalid secret")

    # 2️⃣ Immediately acknowledge (no payload needed)
    response = JSONResponse(status_code=200, content={"status": "ok"})

    # 3️⃣ Do repo build + notify in background
    def _process():
        try:
            if req.round == 1:
                result = generate_app_repo(req)
            elif req.round == 2:
                from .generator_round2 import update_existing_repo_with_llm
                result = update_existing_repo_with_llm(req)
            else:
                raise ValueError(f"Unsupported round {req.round}")

            if req.evaluation_url:
                payload = {
                    "email": req.email,
                    "task": req.task,
                    "round": req.round,
                    "nonce": req.nonce,
                    "repo_url": result.repo_url,
                    "commit_sha": result.commit_sha,
                    "pages_url": result.pages_url,
                }
                notify_with_backoff(req.evaluation_url, payload)
        except Exception as e:
            print("[ERROR] Task processing failed:", e)
            traceback.print_exc()

    background_tasks.add_task(_process)
    return response

# ---- NOTIFY LOG VIEWER ----
@app.get("/_notify_log", include_in_schema=False)
async def _notify_log():
    path = pathlib.Path("/tmp/notify.log")
    if not path.exists():
        return PlainTextResponse("NO LOG: /tmp/notify.log not found\n")
    try:
        return PlainTextResponse(path.read_text(encoding="utf-8"))
    except Exception as e:
        return PlainTextResponse(f"ERROR reading log: {e}\n")
