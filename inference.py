"""Baseline inference script for Email Triage OpenEnv.

Required environment variables:
- API_BASE_URL: LLM endpoint base URL (for OpenAI-compatible APIs)

Optional model variables (used only when LLM is enabled):
- MODEL_NAME: model identifier
- HF_TOKEN or OPENAI_API_KEY: API key for the LLM endpoint

Optional environment variables:
- ENV_BASE_URL: environment URL (default: http://localhost:8000)
- MAX_STEPS_PER_TASK: hard cap on steps per task (default: 40)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI
from dotenv import dotenv_values, load_dotenv

API_BASE_URL = ""
MODEL_NAME = ""
HF_TOKEN = ""
OPENAI_API_KEY = ""
ENV_BASE_URL = "http://localhost:8000"
MAX_STEPS_PER_TASK = 40
FORCE_HEURISTIC = False
TEMPERATURE = 0.0
MAX_TOKENS = 40
VALID_ACTIONS = ["read", "archive", "delete", "flag", "move_to_folder", "mark_spam"]
_FALLBACK_NOTICE_SHOWN = False

SYSTEM_PROMPT = (
    "You are an enterprise email triage assistant. "
    "Return exactly one action from this set: "
    "read, archive, delete, flag, move_to_folder, mark_spam. "
    "No explanation."
)


def require_env() -> None:
    global FORCE_HEURISTIC, MODEL_NAME

    llm_key = HF_TOKEN or OPENAI_API_KEY
    llm_ready = bool(API_BASE_URL and MODEL_NAME and llm_key)
    if llm_ready:
        return

    FORCE_HEURISTIC = True
    if not MODEL_NAME:
        MODEL_NAME = "heuristic-fallback"

    missing = [
        name
        for name, value in {
            "API_BASE_URL": API_BASE_URL,
            "MODEL_NAME": MODEL_NAME if MODEL_NAME != "heuristic-fallback" else "",
            "HF_TOKEN|OPENAI_API_KEY": llm_key,
        }.items()
        if not value
    ]
    print(
        "LLM configuration incomplete "
        f"({', '.join(missing) if missing else 'unknown reason'}). "
        "Using deterministic heuristic policy."
    )


def heuristic_action(email: dict[str, Any]) -> str:
    """Deterministic fallback policy used when LLM calls are unavailable."""

    sender = str(email.get("sender", "")).lower()
    subject = str(email.get("subject", "")).lower()
    preview = str(email.get("preview", "")).lower()
    priority = str(email.get("priority", "")).lower()
    has_attachment = bool(email.get("has_attachment", False))
    text = f"{sender} {subject} {preview}"
    words = set(re.findall(r"[a-z0-9#'-]+", text))

    phishing_markers = [
        "click here",
        "confirm your account",
        "verify your details",
        "you've won",
        "congratulations",
        "winner",
        "sketchy",
        "phishing",
    ]
    if "unknown@" in sender or any(marker in text for marker in phishing_markers):
        return "mark_spam"

    delete_markers = [
        "social",
        "liked your post",
        "youtube",
        "promotion",
        "flash sale",
        "sale",
        "deal",
        "retailer",
    ]
    if any(marker in text for marker in delete_markers):
        return "delete"

    urgent_flag_markers = [
        "contract terms",
        "signature required",
        "invoice",
        "benefits enrollment",
        "deadline",
        "license renewal",
        "renewal reminder",
    ]
    if (any(marker in text for marker in urgent_flag_markers) or "nda" in words) and priority != "low":
        return "flag"

    important_read_markers = [
        "ceo",
        "board meeting",
        "proposal",
        "work sample",
        "project",
        "security",
        "suspicious login",
        "mandatory password reset",
        "account may have been accessed",
        "github",
        "pr review",
        "bank",
    ]
    if any(marker in text for marker in important_read_markers):
        return "read"

    archive_markers = ["weekly digest", "standup summary", "trial is ending", "mentorship"]
    if any(marker in text for marker in archive_markers):
        return "archive"

    if priority == "high":
        return "read"
    if has_attachment and priority == "medium":
        return "read"
    if has_attachment and priority == "high":
        return "flag"
    if priority == "low":
        return "archive"
    return "archive"


def load_runtime_config() -> None:
    """Load env vars from common project locations and initialize globals."""

    global API_BASE_URL, MODEL_NAME, HF_TOKEN, OPENAI_API_KEY, ENV_BASE_URL, MAX_STEPS_PER_TASK, FORCE_HEURISTIC

    root_dir = Path(__file__).resolve().parent
    root_env_path = root_dir / ".env"
    server_env_path = root_dir / "server" / ".env"

    # Keep shell env vars for generic settings, but force inference-critical
    # fields to follow server/.env first so token/model edits take effect.
    load_dotenv(root_env_path, override=False)
    load_dotenv(server_env_path, override=False)

    root_env = dotenv_values(root_env_path)
    server_env = dotenv_values(server_env_path)

    def resolved(name: str, default: str = "") -> str:
        value = server_env.get(name) or os.getenv(name) or root_env.get(name) or default
        return str(value).strip() if value is not None else default

    API_BASE_URL = resolved("API_BASE_URL")
    MODEL_NAME = resolved("MODEL_NAME")
    HF_TOKEN = resolved("HF_TOKEN")
    OPENAI_API_KEY = resolved("OPENAI_API_KEY")
    ENV_BASE_URL = resolved("ENV_BASE_URL", "http://localhost:8000").rstrip("/")
    MAX_STEPS_PER_TASK = int(resolved("MAX_STEPS_PER_TASK", "40"))
    FORCE_HEURISTIC = resolved("FORCE_HEURISTIC", "false").lower() in {"1", "true", "yes", "on"}


def pick_action_with_llm(client: OpenAI, email: dict[str, Any]) -> str:
    global _FALLBACK_NOTICE_SHOWN, FORCE_HEURISTIC

    if FORCE_HEURISTIC or client is None:
        return heuristic_action(email)

    prompt = (
        "Classify this email to one action.\n"
        f"Sender: {email['sender']}\n"
        f"Subject: {email['subject']}\n"
        f"Preview: {email['preview']}\n"
        f"Priority: {email['priority']}\n"
        f"Has Attachment: {email['has_attachment']}\n"
        "Return only the action token."
    )

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        text = (completion.choices[0].message.content or "").strip().lower()
        # Normalize accidental formatting.
        token = text.split()[0].strip("`'\".,:;()[]{}") if text else ""
        if token in VALID_ACTIONS:
            return token

        for action in VALID_ACTIONS:
            if action in text:
                return action
        return "archive"
    except Exception as exc:  # noqa: BLE001
        if not _FALLBACK_NOTICE_SHOWN:
            print(f"LLM request failed ({exc}). Falling back to deterministic heuristic policy.")
            _FALLBACK_NOTICE_SHOWN = True
        FORCE_HEURISTIC = True
        return heuristic_action(email)


def run_task(client: OpenAI, task: str) -> dict[str, Any]:
    try:
        # Emit structured START block for validator.
        print(f"[START] task={task}", flush=True)
        
        with httpx.Client(timeout=30.0) as http:
            reset = http.post(f"{ENV_BASE_URL}/reset", json={"task": task})
            reset.raise_for_status()

            done = False
            steps = 0
            step_reward_sum = 0.0

            while not done and steps < MAX_STEPS_PER_TASK:
                obs_resp = http.get(f"{ENV_BASE_URL}/observation")
                obs_resp.raise_for_status()
                obs = obs_resp.json()
                current_email = obs.get("current_email")

                if current_email is None:
                    break

                action = pick_action_with_llm(client, current_email)
                step = http.post(
                    f"{ENV_BASE_URL}/step",
                    json={"action": action, "email_id": current_email["id"], "details": {}},
                )
                step.raise_for_status()
                payload = step.json()

                reward_obj = payload.get("reward", {})
                step_reward = float(reward_obj.get("score", 0.0))
                step_reward_sum += step_reward
                done = bool(payload.get("done", False))
                steps += 1
                
                # Emit structured STEP block for each action.
                print(f"[STEP] step={steps} reward={step_reward:.4f}", flush=True)

            grade = http.get(f"{ENV_BASE_URL}/grade")
            grade.raise_for_status()
            grade_json = grade.json()

            total_emails = grade_json.get("total_emails", 1)
            normalized_trajectory_reward = step_reward_sum / total_emails if total_emails > 0 else 0.0
            grader_score = float(grade_json.get("score", 0.0))

            # Emit structured END block for validator.
            print(f"[END] task={task} score={grader_score:.4f} steps={steps}", flush=True)

            return {
                "task": task,
                "steps": steps,
                "normalized_trajectory_reward": round(normalized_trajectory_reward, 4),
                "grader_score": grader_score,
                "grader_status": grade_json.get("status", "unknown"),
                "grader_breakdown": grade_json.get("breakdown", {}),
            }
    except Exception as exc:  # noqa: BLE001
        print(f"[END] task={task} score=0.0 steps=0", flush=True)
        print(f"Task '{task}' failed: {exc}", flush=True)
        return {
            "task": task,
            "steps": 0,
            "normalized_trajectory_reward": 0.0,
            "grader_score": 0.0,
            "grader_status": "error",
            "grader_breakdown": {},
            "error": str(exc),
        }


def build_client() -> OpenAI | None:
    if FORCE_HEURISTIC:
        return None
    try:
        return OpenAI(base_url=API_BASE_URL, api_key=(HF_TOKEN or OPENAI_API_KEY))
    except Exception as exc:  # noqa: BLE001
        print(f"OpenAI client initialization failed ({exc}). Using deterministic heuristic policy.")
        return None


def main() -> None:
    load_runtime_config()
    require_env()
    client = build_client()

    tasks = ["easy", "medium", "hard"]
    results = [run_task(client, task) for task in tasks]
    avg = sum(item["grader_score"] for item in results) / len(results)

    output = {
        "env_base_url": ENV_BASE_URL,
        "model_name": MODEL_NAME,
        "temperature": TEMPERATURE,
        "tasks": results,
        "average_score": round(avg, 4),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        output = {
            "env_base_url": ENV_BASE_URL,
            "model_name": MODEL_NAME or "heuristic-fallback",
            "temperature": TEMPERATURE,
            "tasks": [],
            "average_score": 0.0,
            "error": str(exc),
        }
        print(json.dumps(output, indent=2))
