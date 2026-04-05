# Server: Email Triage OpenEnv

FastAPI backend implementing a real-world email triage OpenEnv environment.

## Run

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Endpoints

- `POST /reset` with `{"task": "easy|medium|hard"}`
- `POST /step` with `{"action": "...", "email_id": "...", "details": {}}`
- `GET /state`
- `GET /observation`
- `GET /grade`
- `GET /tasks`
- `GET /health`

## Notes

- `step` returns `observation`, `reward`, `done`, `info`, and `state`
- reward is trajectory-shaped and includes partial progress
- grading is deterministic per task with score range `[0.0, 1.0]`
- OpenEnv metadata is in `openenv.yaml`
