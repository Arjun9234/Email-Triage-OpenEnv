"""Baseline inference script for Email Triage OpenEnv.

Required environment variables:
- API_BASE_URL: LLM endpoint base URL (for OpenAI-compatible APIs)
- API_KEY: API key for the provided LiteLLM proxy

Optional environment variables:
- MODEL_NAME: model identifier (default: gpt-4o-mini)
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
from dotenv import load_dotenv
from openai import OpenAI

API_BASE_URL = ""
API_KEY = ""
MODEL_NAME = ""
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


def load_runtime_config() -> None:
    """Load environment variables injected by the validator."""
    global API_BASE_URL, API_KEY, MODEL_NAME, ENV_BASE_URL, MAX_STEPS_PER_TASK, FORCE_HEURISTIC

    load_dotenv(Path(__file__).resolve().parent / "server" / ".env")

    API_BASE_URL = os.environ.get("API_BASE_URL", "").strip()
    API_KEY = os.environ.get("API_KEY", "").strip()
    MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini").strip()
    ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:8000").rstrip("/")
    MAX_STEPS_PER_TASK = int(os.environ.get("MAX_STEPS_PER_TASK", "40"))
    FORCE_HEURISTIC = False


def require_env() -> None:
    """Decide whether to use proxy LLM or heuristic fallback."""
    global FORCE_HEURISTIC, MODEL_NAME

    has_api_proxy = bool(API_BASE_URL and API_KEY)

    if has_api_proxy:
        FORCE_HEURISTIC = False
        if not MODEL_NAME:
            MODEL_NAME = "gpt-4o-mini"
        return

    FORCE_HEURISTIC = True
    if not MODEL_NAME:
        MODEL_NAME = "heuristic-fallback"

    print(
        f"No validator LLM proxy available. Using deterministic heuristic policy. "
        f"(API_BASE_URL={'set' if API_BASE_URL else 'empty'}, "
        f"API_KEY={'set' if API_KEY else 'empty'}, "
        f"MODEL_NAME={'set' if MODEL_NAME else 'empty'})",
        flush=True
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


def build_client() -> OpenAI | None:
    """Create OpenAI-compatible client using ONLY validator-provided proxy."""
    if not API_BASE_URL:
        print("Missing API_BASE_URL. Using heuristic policy.", flush=True)
        return None

    if not API_KEY:
        print("Missing API_KEY. Using heuristic policy.", flush=True)
        return None

    try:
        return OpenAI(
            base_url=API_BASE_URL,
            api_key=API_KEY
        )
    except Exception as exc:  # noqa: BLE001
        print(f"OpenAI client initialization failed ({exc}). Using heuristic policy.", flush=True)
        return None


def pick_action_with_llm(client: OpenAI | None, email: dict[str, Any]) -> str:
    global _FALLBACK_NOTICE_SHOWN, FORCE_HEURISTIC

    if FORCE_HEURISTIC or client is None or not MODEL_NAME:
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
        token = text.split()[0].strip("`'\".,:;()[]{}") if text else ""

        if token in VALID_ACTIONS:
            return token

        for action in VALID_ACTIONS:
            if action in text:
                return action

        return "archive"

    except Exception as exc:  # noqa: BLE001
        if not _FALLBACK_NOTICE_SHOWN:
            print(f"LLM request failed ({exc}). Falling back to deterministic heuristic policy.", flush=True)
            _FALLBACK_NOTICE_SHOWN = True
        FORCE_HEURISTIC = True
        return heuristic_action(email)


def run_task(client: OpenAI | None, task: str) -> dict[str, Any]:
    try:
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

                print(f"[STEP] step={steps} reward={step_reward:.4f}", flush=True)

            grade = http.get(f"{ENV_BASE_URL}/grade")
            grade.raise_for_status()
            grade_json = grade.json()

            total_emails = grade_json.get("total_emails", 1)
            normalized_trajectory_reward = step_reward_sum / total_emails if total_emails > 0 else 0.0
            grader_score = float(grade_json.get("score", 0.0))

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


def main() -> None:
    load_runtime_config()

    api_url_display = f"{API_BASE_URL[:50]}..." if len(API_BASE_URL) > 50 else API_BASE_URL
    print(f"[DEBUG] API_BASE_URL={api_url_display if API_BASE_URL else '<empty>'}", flush=True)
    print(f"[DEBUG] API_KEY={'<set>' if API_KEY else '<empty>'}", flush=True)
    print(f"[DEBUG] MODEL_NAME={MODEL_NAME if MODEL_NAME else '<empty>'}", flush=True)
    print(f"[DEBUG] FORCE_HEURISTIC={FORCE_HEURISTIC} (before require_env)", flush=True)

    require_env()

    print(f"[DEBUG] FORCE_HEURISTIC={FORCE_HEURISTIC} (after require_env)", flush=True)
    print(f"[DEBUG] MODEL_NAME={MODEL_NAME} (after require_env)", flush=True)

    client = build_client()
    print(f"[DEBUG] client={'<created>' if client else '<None>'}", flush=True)

    if client and not FORCE_HEURISTIC:
        print(f"[DEBUG] Using validator-injected API: {api_url_display} with model={MODEL_NAME}", flush=True)
    else:
        print(f"[DEBUG] No validator API available. Using heuristic fallback.", flush=True)

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
