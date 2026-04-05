# Email Triage OpenEnv (Real-World Workflow Environment)

This project implements a complete OpenEnv environment that simulates a real inbox triage workflow used by operations, support, and business teams.

The environment is designed for agent training/evaluation through standard APIs:

- `reset()`
- `step(action)`
- `state()`

The server now persists session state to disk (`server/.runtime/sessions.json`), so frontend dashboard progress and scores survive browser refresh and backend restarts.

It includes deterministic task graders, shaped rewards, reproducible baseline inference, and containerized deployment for Hugging Face Spaces.

## Why this is real-world

Email triage is a daily operational task in every organization:

- prioritizing high-risk alerts (security, legal, finance)
- filtering spam/phishing
- routing informational mail vs action-required mail
- maintaining throughput without missing critical messages

## OpenEnv API and Typed Models

Backend implementation is in `server/email_triage_env.py` + `server/main.py`.

Typed models (Pydantic):

- `Action`: `action`, `email_id`, `details`
- `Observation`: task metadata, current email, inbox snapshot, progress message
- `Reward`: shaped scalar reward with progress and cumulative normalized score
- `GraderResult`: deterministic score in `[0.0, 1.0]`

HTTP endpoints:

- `POST /reset` -> initial observation
- `POST /step` -> observation, reward, done, info, state
- `GET /state` -> current environment state
- `GET /grade` -> deterministic task score `[0.0, 1.0]`
- `GET /tasks` -> available task catalog
- `GET /observation` -> current observation snapshot

OpenEnv metadata file:

- `server/openenv.yaml`

## Action Space

Discrete actions:

- `read`
- `archive`
- `delete`
- `flag`
- `move_to_folder`
- `mark_spam`

## Observation Space

Structured observation includes:

- task metadata (id, difficulty, max steps)
- inbox counts
- `current_email` object
- full email metadata list with action history
- status message

## Reward Function (Meaningful trajectory signals)

Per-step shaping:

- exact action match: `+1.00`
- partial safe handling on important mail: `+0.35`
- wrong action: `-0.10`
- invalid/repeated action: `-0.25`

Additional mechanics:

- progress signal: `processed / total`
- loop prevention via max-step boundary
- normalized cumulative trajectory score in `[0.0, 1.0]`

## Tasks and Graders (Easy -> Medium -> Hard)

### 1) Easy: Basic Email Management

- 5 emails
- Goal: accurate basic triage
- Deterministic grader: `0.85 * accuracy + 0.15 * completion`

### 2) Medium: Smart Email Organization

- 8 emails
- Goal: accurate triage + spam/phishing handling
- Deterministic grader: `0.65 * accuracy + 0.25 * spam_precision + 0.10 * completion`

### 3) Hard: Executive Inbox Prioritization

- 10 emails
- Goal: high-priority correctness + efficient completion
- Deterministic grader:
  `0.55 * accuracy + 0.35 * high_priority_recall + 0.10 * completion - efficiency_penalty`

All graders always return `score` in `[0.0, 1.0]`.

## Baseline Inference (Required file at repo root)

Baseline script:

- `inference.py` (root-level, mandatory)
- Uses OpenAI client and required env vars:
  - `API_BASE_URL`
  - `MODEL_NAME`
  - `HF_TOKEN` (or `OPENAI_API_KEY`)

Optional variable:

- `ENV_BASE_URL` (default `http://localhost:8000`)

Run baseline:

```bash
python inference.py
```

Output is deterministic JSON summary (temperature fixed at `0.0`) with per-task scores and average score.

## Setup and Run

### Local Python run

```bash
cd server
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Server starts on `http://localhost:8000`.

### Docker run

```bash
docker build -t email-triage-openenv:latest .
docker run --rm -p 8000:8000 email-triage-openenv:latest
```

## Hugging Face Spaces (Docker)

- Use root `Dockerfile`
- Set Space to Docker SDK
- Add `openenv` tag in Space metadata
- Expose port `8000`

## Pre-submission Validation Commands

Start server locally first (terminal 1):

```bash
cd server
python main.py
```

Then run checks (terminal 2):

```bash
# 1) OpenEnv spec validation
openenv validate

# 2) Docker build check
docker build -t email-triage-openenv:latest .

# 3) Run baseline (requires LLM env vars)
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="YOUR_MODEL"
export HF_TOKEN="YOUR_HF_TOKEN"
python inference.py
```

Optional one-shot script:

```bash
bash scripts/validate-submission.sh https://YOUR_SPACE.hf.space .
```

## Reproducibility Notes

- deterministic environment and fixed task datasets
- deterministic graders
- fixed inference decoding params (`temperature=0.0`)
- no random action sampling in baseline
