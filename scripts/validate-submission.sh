#!/usr/bin/env bash
set -euo pipefail

SPACE_URL="${1:-}"
REPO_DIR="${2:-.}"

if [ -z "$SPACE_URL" ]; then
  echo "Usage: $0 <space_url> [repo_dir]"
  echo "Example: $0 https://my-space.hf.space ."
  exit 1
fi

SPACE_URL="${SPACE_URL%/}"
cd "$REPO_DIR"

echo "[1/5] Ping HF Space /reset"
HTTP_CODE=$(curl -s -o /tmp/openenv_ping_body.txt -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -d '{"task":"easy"}' \
  "$SPACE_URL/reset" --max-time 30 || echo "000")

if [ "$HTTP_CODE" != "200" ]; then
  echo "FAIL: /reset returned $HTTP_CODE"
  cat /tmp/openenv_ping_body.txt || true
  exit 1
fi

echo "PASS: Space responds to /reset"

echo "[2/5] Docker build"
docker build -t email-triage-openenv:latest .
echo "PASS: Docker build"

echo "[3/5] OpenEnv validate"
openenv validate

echo "[4/5] Task grader smoke test"
python - <<'PY'
import requests

base = "http://localhost:8000"
for task in ["easy", "medium", "hard"]:
    r = requests.post(f"{base}/reset", json={"task": task}, timeout=10)
    r.raise_for_status()
    for _ in range(40):
        o = requests.get(f"{base}/observation", timeout=10).json()
        email = o.get("current_email")
        if not email:
            break
        action = "archive"
        requests.post(
            f"{base}/step",
            json={"action": action, "email_id": email["id"], "details": {}},
            timeout=10,
        ).raise_for_status()
    g = requests.get(f"{base}/grade", timeout=10).json()
    score = float(g.get("score", 0.0))
    assert 0.0 <= score <= 1.0, f"Score out of range for {task}: {score}"
print("PASS: grader scores are in [0.0, 1.0] for all tasks")
PY

echo "[5/5] Baseline inference reproducibility"
python inference.py

echo "All validation checks passed."
