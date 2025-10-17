import time, json, requests, os, datetime, traceback

DEFAULT_DELAYS = [1, 2, 4, 8, 16]
LOG_PATH = "/tmp/notify.log"

def _log(line: str):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    msg = f"[notify] {ts} {line}"
    print(msg, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        # best-effort; don't crash notifier
        pass

def notify_with_backoff(evaluation_url: str, payload: dict, delays=DEFAULT_DELAYS) -> bool:
    headers = {"Content-Type": "application/json"}
    for delay in [0] + list(delays):
        if delay:
            _log(f"sleep {delay}s before retry")
            time.sleep(delay)
        try:
            _log(f"POST {evaluation_url} payload keys: {list(payload.keys())}")
            r = requests.post(evaluation_url, json=payload, headers=headers, timeout=20)
            _log(f"response: status={r.status_code} len={len(r.text)}")
            if 200 <= r.status_code < 300:
                return True
        except Exception as e:
            _log("exception: " + "".join(traceback.format_exception_only(type(e), e)).strip())
    _log("giving up after retries")
    return False
