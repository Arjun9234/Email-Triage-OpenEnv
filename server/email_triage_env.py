"""Email triage OpenEnv environment with deterministic grading."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

SCORE_EPSILON = 1e-6


def clamp_open_score(value: float) -> float:
    """Force any score strictly inside (0, 1) with no endpoint leakage."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.5

    if value <= 0.0:
        return SCORE_EPSILON
    if value >= 1.0:
        return 1.0 - SCORE_EPSILON
    return value


class EmailPriority(str, Enum):
    """Email priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EmailAction(str, Enum):
    """Available actions for email triage"""
    READ = "read"
    ARCHIVE = "archive"
    DELETE = "delete"
    FLAG = "flag"
    MOVE_TO_FOLDER = "move_to_folder"
    MARK_SPAM = "mark_spam"


class Email(BaseModel):
    """Email model"""
    id: str
    sender: str
    subject: str
    preview: str
    priority: EmailPriority
    has_attachment: bool = False
    is_read: bool = False


class TaskMetadata(BaseModel):
    """Task-level metadata presented to the agent."""
    id: str
    name: str
    description: str
    difficulty: str
    max_steps: int


class Observation(BaseModel):
    """Agent observation state"""
    task: TaskMetadata
    inbox_count: int
    unread_count: int
    current_email: Optional[Email] = None
    email_list: list[dict] = Field(default_factory=list)
    action_taken: Optional[str] = None
    message: str = ""


class Action(BaseModel):
    """Agent action"""
    action: EmailAction
    email_id: str
    details: Optional[dict] = None


class Reward(BaseModel):
    """Reward signal"""
    score: float = Field(ge=-1.0, le=1.0)
    reason: str
    progress: float = Field(ge=0.0, le=1.0)
    cumulative_score: float


class StepInfo(BaseModel):
    """Additional info returned by step for diagnostics."""
    expected_action: str
    was_repeat: bool
    was_valid: bool
    processed_count: int
    total_count: int


class GraderResult(BaseModel):
    """Deterministic task grader output strictly inside (0.0, 1.0)."""
    task: str
    score: float = Field(gt=0.0, lt=1.0)
    status: str
    message: str
    breakdown: dict[str, float]
    total_actions: int
    total_emails: int


class EmailTriageEnv:
    """OpenEnv Email Triage Environment"""

    TASKS = {
        "easy": {
            "name": "Basic Email Management",
            "description": "Sort 5 emails into appropriate categories",
            "difficulty": "easy",
            "max_steps": 14,
            "emails": [
                {
                    "id": "email_1",
                    "sender": "boss@company.com",
                    "subject": "Q4 Performance Review",
                    "preview": "Your performance review is ready for discussion...",
                    "priority": "high",
                    "has_attachment": True,
                },
                {
                    "id": "email_2",
                    "sender": "newsletter@medium.com",
                    "subject": "Your weekly digest",
                    "preview": "Here are the top stories this week...",
                    "priority": "low",
                    "has_attachment": False,
                },
                {
                    "id": "email_3",
                    "sender": "support@vendor.com",
                    "subject": "License renewal reminder",
                    "preview": "Your license expires in 30 days...",
                    "priority": "medium",
                    "has_attachment": False,
                },
                {
                    "id": "email_4",
                    "sender": "noreply@social.com",
                    "subject": "Someone liked your post",
                    "preview": "Your post got 50 likes!...",
                    "priority": "low",
                    "has_attachment": False,
                },
                {
                    "id": "email_5",
                    "sender": "alerts@bank.com",
                    "subject": "Suspicious login detected",
                    "preview": "We detected an unusual login from...",
                    "priority": "high",
                    "has_attachment": False,
                },
            ],
            "correct_actions": {
                "email_1": "read",
                "email_2": "archive",
                "email_3": "flag",
                "email_4": "delete",
                "email_5": "read",
            },
        },
        "medium": {
            "name": "Smart Email Organization",
            "description": "Triage 8 emails with attachment handling",
            "difficulty": "medium",
            "max_steps": 22,
            "emails": [
                {
                    "id": "email_1",
                    "sender": "client@startup.io",
                    "subject": "Project proposal attached",
                    "preview": "Please review the attached proposal...",
                    "priority": "high",
                    "has_attachment": True,
                },
                {
                    "id": "email_2",
                    "sender": "team@slack.com",
                    "subject": "Daily standup summary",
                    "preview": "Here's what the team completed...",
                    "priority": "medium",
                    "has_attachment": False,
                },
                {
                    "id": "email_3",
                    "sender": "unknown@sketchy.ru",
                    "subject": "Click here to confirm your account",
                    "preview": "Please verify your details immediately...",
                    "priority": "high",
                    "has_attachment": False,
                },
                {
                    "id": "email_4",
                    "sender": "hr@company.com",
                    "subject": "Benefits enrollment deadline",
                    "preview": "Enrollment closes in 2 days...",
                    "priority": "high",
                    "has_attachment": True,
                },
                {
                    "id": "email_5",
                    "sender": "deals@retailer.com",
                    "subject": "50% off everything this weekend",
                    "preview": "Limited time sale...",
                    "priority": "low",
                    "has_attachment": False,
                },
                {
                    "id": "email_6",
                    "sender": "noreply@github.com",
                    "subject": "PR review requested",
                    "preview": "Your code review is needed on PR #234...",
                    "priority": "medium",
                    "has_attachment": False,
                },
                {
                    "id": "email_7",
                    "sender": "invoice@vendor.com",
                    "subject": "Invoice #INV-2024-001",
                    "preview": "Payment due within 30 days...",
                    "priority": "medium",
                    "has_attachment": True,
                },
                {
                    "id": "email_8",
                    "sender": "spam@marketing.com",
                    "subject": "Congratulations, you've won!",
                    "preview": "You've been selected as a winner...",
                    "priority": "low",
                    "has_attachment": False,
                },
            ],
            "correct_actions": {
                "email_1": "read",
                "email_2": "archive",
                "email_3": "mark_spam",
                "email_4": "flag",
                "email_5": "delete",
                "email_6": "read",
                "email_7": "flag",
                "email_8": "mark_spam",
            },
        },
        "hard": {
            "name": "Expert Email Management",
            "description": "Triage 10 complex emails requiring contextual understanding",
            "difficulty": "hard",
            "max_steps": 30,
            "emails": [
                {
                    "id": "email_1",
                    "sender": "ceo@company.com",
                    "subject": "Fwd: Board meeting agenda",
                    "preview": "Please find attached the agenda for Friday's board...",
                    "priority": "high",
                    "has_attachment": True,
                },
                {
                    "id": "email_2",
                    "sender": "contractor@freelance.net",
                    "subject": "Work sample for review",
                    "preview": "I've completed the initial design work...",
                    "priority": "medium",
                    "has_attachment": True,
                },
                {
                    "id": "email_3",
                    "sender": "security@company.com",
                    "subject": "Mandatory password reset required",
                    "preview": "For security compliance, please reset your password...",
                    "priority": "high",
                    "has_attachment": False,
                },
                {
                    "id": "email_4",
                    "sender": "partner@bigcorp.com",
                    "subject": "RE: Contract terms discussion",
                    "preview": "Thank you for your email. We've reviewed the terms...",
                    "priority": "high",
                    "has_attachment": True,
                },
                {
                    "id": "email_5",
                    "sender": "support@saas.com",
                    "subject": "Your trial is ending soon",
                    "preview": "Your 14-day trial expires in 3 days...",
                    "priority": "medium",
                    "has_attachment": False,
                },
                {
                    "id": "email_6",
                    "sender": "noreply@youtube.com",
                    "subject": "A channel you subscribed to posted",
                    "preview": "Tech Channel uploaded: 'Top 10 Tools 2024'...",
                    "priority": "low",
                    "has_attachment": False,
                },
                {
                    "id": "email_7",
                    "sender": "legal@company.com",
                    "subject": "NDA signature required - Urgent",
                    "preview": "We need your signature on the attached NDA...",
                    "priority": "high",
                    "has_attachment": True,
                },
                {
                    "id": "email_8",
                    "sender": "team-lead@company.com",
                    "subject": "Mentorship opportunity for junior engineer",
                    "preview": "Would you be interested in mentoring a new hire?...",
                    "priority": "medium",
                    "has_attachment": False,
                },
                {
                    "id": "email_9",
                    "sender": "noreply@twitter.com",
                    "subject": "Your account may have been accessed",
                    "preview": "We detected unusual login activity. If this...",
                    "priority": "high",
                    "has_attachment": False,
                },
                {
                    "id": "email_10",
                    "sender": "promotions@vendor.com",
                    "subject": "Flash sale: Software licenses",
                    "preview": "Limited offer: 40% off all licenses...",
                    "priority": "low",
                    "has_attachment": False,
                },
            ],
            "correct_actions": {
                "email_1": "read",
                "email_2": "read",
                "email_3": "read",
                "email_4": "flag",
                "email_5": "archive",
                "email_6": "delete",
                "email_7": "flag",
                "email_8": "archive",
                "email_9": "read",
                "email_10": "delete",
            },
        },
    }

    def __init__(self, task: str = "easy"):
        """Initialize the environment with a specific task"""
        if task not in self.TASKS:
            raise ValueError(f"Task must be one of {list(self.TASKS.keys())}")

        self.task_name = task
        self.task_config = self.TASKS[task]
        self.emails = [Email(**email) for email in self.task_config["emails"]]
        self.correct_actions = self.task_config["correct_actions"]

        self.current_email_index = 0
        self.actions_taken: dict[str, str] = {}
        self.action_history: list[dict[str, str]] = []
        self.cumulative_reward = 0.0
        self.correct_action_count = 0
        self.step_count = 0
        self.max_steps = int(self.task_config["max_steps"])

    def reset(self) -> Observation:
        """Reset the environment and return initial observation"""
        self.current_email_index = 0
        self.actions_taken = {}
        self.action_history = []
        self.cumulative_reward = 0.0
        self.correct_action_count = 0
        self.step_count = 0
        return self._get_observation("Environment reset")

    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        """
        Execute an action and return observation, reward, done, and info.

        Reward shaping:
        - +1.00 exact action match
        - +0.35 partial credit for high-priority safe handling
        - -0.10 for wrong action
        - -0.25 for invalid/repeated/destructive loop-like action
        """
        self.step_count += 1

        processed_count = len(self.actions_taken)
        total_count = len(self.emails)

        # Validate action
        if action.email_id not in [e.id for e in self.emails]:
            reward = Reward(
                score=-0.25,
                reason="Invalid email ID",
                progress=processed_count / total_count,
                cumulative_score=self._normalized_cumulative_score(),
            )
            obs = self._get_observation(f"Invalid email ID: {action.email_id}")
            info = StepInfo(
                expected_action="unknown",
                was_repeat=False,
                was_valid=False,
                processed_count=processed_count,
                total_count=total_count,
            )
            done = self.step_count >= self.max_steps
            if done:
                obs = self._get_observation("Max steps reached")
            return obs, reward, done, info.model_dump()

        if action.email_id in self.actions_taken:
            reward = Reward(
                score=-0.25,
                reason="Email already processed",
                progress=processed_count / total_count,
                cumulative_score=self._normalized_cumulative_score(),
            )
            obs = self._get_observation(f"Email already processed: {action.email_id}")
            info = StepInfo(
                expected_action=self.correct_actions[action.email_id],
                was_repeat=True,
                was_valid=True,
                processed_count=processed_count,
                total_count=total_count,
            )
            done = self.step_count >= self.max_steps
            if done:
                obs = self._get_observation("Max steps reached")
            return obs, reward, done, info.model_dump()

        # Check if correct action
        correct_action = self.correct_actions[action.email_id]
        is_correct = action.action.value == correct_action

        # Partial credit for cautious handling of important/security-like items
        partial_credit = 0.0
        if (
            not is_correct
            and correct_action in {"read", "flag"}
            and action.action.value in {"read", "flag"}
        ):
            partial_credit = 0.35

        if is_correct:
            reward_score = 1.0
            self.correct_action_count += 1
        elif partial_credit > 0.0:
            reward_score = partial_credit
        else:
            reward_score = -0.10

        self.cumulative_reward += reward_score
        self.actions_taken[action.email_id] = action.action.value
        self.action_history.append(
            {
                "email_id": action.email_id,
                "action": action.action.value,
                "expected": correct_action,
            }
        )

        processed_count = len(self.actions_taken)

        # Determine if done
        done = processed_count == total_count or self.step_count >= self.max_steps

        reason = (
            f"Correct action (expected: {correct_action})"
            if is_correct
            else (
                f"Partially correct handling (expected: {correct_action}, got: {action.action.value})"
                if partial_credit > 0.0
                else f"Incorrect action (expected: {correct_action}, got: {action.action.value})"
            )
        )

        reward = Reward(
            score=reward_score,
            reason=reason,
            progress=processed_count / total_count,
            cumulative_score=self._normalized_cumulative_score(),
        )

        # Move to next email
        if done and processed_count == total_count:
            self.current_email_index = len(self.emails)
            obs = self._get_observation("Task completed")
        elif done:
            obs = self._get_observation("Episode ended due to max steps")
        else:
            self.current_email_index = self._next_unprocessed_index()
            obs = self._get_observation(f"Action recorded: {action.action.value}")

        info = StepInfo(
            expected_action=correct_action,
            was_repeat=False,
            was_valid=True,
            processed_count=processed_count,
            total_count=total_count,
        )
        return obs, reward, done, info.model_dump()

    def _normalized_cumulative_score(self) -> float:
        """Normalized cumulative score strictly inside (0, 1)."""
        if not self.emails:
            return SCORE_EPSILON
        raw = self.cumulative_reward / len(self.emails)
        return clamp_open_score(raw)

    def _next_unprocessed_index(self) -> int:
        """Find next unprocessed email index."""
        for idx, email in enumerate(self.emails):
            if email.id not in self.actions_taken:
                return idx
        return len(self.emails)

    def _get_observation(self, message: str = "") -> Observation:
        """Generate observation state"""
        current_email = None
        if self.current_email_index < len(self.emails):
            current_email = self.emails[self.current_email_index]

        email_list = [
            {
                "id": e.id,
                "sender": e.sender,
                "subject": e.subject,
                "preview": e.preview,
                "priority": e.priority.value,
                "has_attachment": e.has_attachment,
                "is_read": e.is_read,
                "action_taken": self.actions_taken.get(e.id),
            }
            for e in self.emails
        ]

        return Observation(
            task=TaskMetadata(
                id=self.task_name,
                name=self.task_config["name"],
                description=self.task_config["description"],
                difficulty=self.task_config["difficulty"],
                max_steps=self.max_steps,
            ),
            inbox_count=len(self.emails),
            unread_count=len(self.emails) - len(self.actions_taken),
            current_email=current_email,
            email_list=email_list,
            message=message,
        )

    def state(self) -> dict:
        """Get current environment state (OpenEnv state API)."""
        return {
            "task": self.task_name,
            "task_description": self.task_config["description"],
            "step_count": self.step_count,
            "max_steps": self.max_steps,
            "cumulative_reward": round(self.cumulative_reward, 4),
            "normalized_score": clamp_open_score(self._normalized_cumulative_score()),
            "correct_action_count": self.correct_action_count,
            "actions_taken": self.actions_taken,
            "progress": f"{len(self.actions_taken)}/{len(self.emails)}",
            "done": len(self.actions_taken) == len(self.emails) or self.step_count >= self.max_steps,
        }

    def get_state(self) -> dict:
        """Backwards-compatible alias."""
        return self.state()

    def export_session_state(self) -> dict:
        """Serialize environment internals for persistence across process lifecycles."""
        return {
            "task": self.task_name,
            "current_email_index": self.current_email_index,
            "actions_taken": dict(self.actions_taken),
            "action_history": list(self.action_history),
            "cumulative_reward": float(self.cumulative_reward),
            "correct_action_count": int(self.correct_action_count),
            "step_count": int(self.step_count),
            "max_steps": int(self.max_steps),
        }

    @classmethod
    def from_session_state(cls, data: dict) -> "EmailTriageEnv":
        """Rebuild environment from persisted session state."""
        task = str(data.get("task", "easy"))
        env = cls(task=task)

        env.current_email_index = int(data.get("current_email_index", 0))
        env.actions_taken = {
            str(email_id): str(action)
            for email_id, action in dict(data.get("actions_taken", {})).items()
        }
        env.action_history = [
            {
                "email_id": str(item.get("email_id", "")),
                "action": str(item.get("action", "")),
                "expected": str(item.get("expected", "")),
            }
            for item in list(data.get("action_history", []))
            if isinstance(item, dict)
        ]
        env.cumulative_reward = float(data.get("cumulative_reward", 0.0))
        env.correct_action_count = int(data.get("correct_action_count", 0))
        env.step_count = int(data.get("step_count", 0))
        env.max_steps = int(data.get("max_steps", env.task_config["max_steps"]))

        # Clamp pointer to a valid inbox index in case persisted data was stale.
        env.current_email_index = max(0, min(env.current_email_index, len(env.emails)))
        return env

    def _grade_easy(self) -> GraderResult:
        total = len(self.emails)
        exact_correct = sum(
            1 for email in self.emails if self.actions_taken.get(email.id) == self.correct_actions[email.id]
        )
        completion_ratio = len(self.actions_taken) / total
        accuracy = exact_correct / total

        raw_score = 0.85 * accuracy + 0.15 * completion_ratio
        score = clamp_open_score(raw_score)

        return GraderResult(
            task=self.task_name,
            score=score,
            status="complete" if completion_ratio == 1.0 else "incomplete",
            message="Easy grader: accuracy-first with light completion bonus",
            breakdown={
                "accuracy": round(accuracy, 4),
                "completion": round(completion_ratio, 4),
            },
            total_actions=len(self.actions_taken),
            total_emails=total,
        )

    def _grade_medium(self) -> GraderResult:
        total = len(self.emails)
        exact_correct = sum(
            1 for email in self.emails if self.actions_taken.get(email.id) == self.correct_actions[email.id]
        )
        spam_targets = {
            eid for eid, expected in self.correct_actions.items() if expected == "mark_spam"
        }
        spam_correct = sum(
            1 for eid in spam_targets if self.actions_taken.get(eid) == "mark_spam"
        )
        completion_ratio = len(self.actions_taken) / total
        accuracy = exact_correct / total
        spam_precision = spam_correct / max(1, len(spam_targets))

        raw_score = 0.65 * accuracy + 0.25 * spam_precision + 0.10 * completion_ratio
        score = clamp_open_score(raw_score)

        return GraderResult(
            task=self.task_name,
            score=score,
            status="complete" if completion_ratio == 1.0 else "incomplete",
            message="Medium grader: balances general accuracy with spam/phishing detection",
            breakdown={
                "accuracy": round(accuracy, 4),
                "spam_precision": round(spam_precision, 4),
                "completion": round(completion_ratio, 4),
            },
            total_actions=len(self.actions_taken),
            total_emails=total,
        )

    def _grade_hard(self) -> GraderResult:
        total = len(self.emails)
        exact_correct = sum(
            1 for email in self.emails if self.actions_taken.get(email.id) == self.correct_actions[email.id]
        )
        high_priority_ids = {email.id for email in self.emails if email.priority == EmailPriority.HIGH}
        high_priority_correct = sum(
            1 for eid in high_priority_ids if self.actions_taken.get(eid) == self.correct_actions[eid]
        )

        completion_ratio = len(self.actions_taken) / total
        accuracy = exact_correct / total
        high_priority_recall = high_priority_correct / max(1, len(high_priority_ids))

        efficiency_penalty = 0.0
        if self.step_count > total:
            efficiency_penalty = min(0.20, (self.step_count - total) / total * 0.05)

        raw_score = (
            0.55 * accuracy
            + 0.35 * high_priority_recall
            + 0.10 * completion_ratio
            - efficiency_penalty
        )
        score = clamp_open_score(raw_score)

        return GraderResult(
            task=self.task_name,
            score=score,
            status="complete" if completion_ratio == 1.0 else "incomplete",
            message="Hard grader: prioritizes high-risk mail handling and efficiency",
            breakdown={
                "accuracy": round(accuracy, 4),
                "high_priority_recall": round(high_priority_recall, 4),
                "completion": round(completion_ratio, 4),
                "efficiency_penalty": round(efficiency_penalty, 4),
            },
            total_actions=len(self.actions_taken),
            total_emails=total,
        )

    def grade(self) -> dict:
        """Run deterministic per-task grader and return scores strictly inside (0, 1)."""
        if self.task_name == "easy":
            result = self._grade_easy()
        elif self.task_name == "medium":
            result = self._grade_medium()
        else:
            result = self._grade_hard()

        payload = result.model_dump()

        # Hard clamp all outward-facing score fields
        payload["score"] = clamp_open_score(payload.get("score", 0.5))
        payload["normalized_trajectory_reward"] = clamp_open_score(self._normalized_cumulative_score())

        return payload