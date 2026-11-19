"""A task data model and its standard-library unit tests."""

from __future__ import annotations

import json
import unittest
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Dict, Iterable, List, Optional
from uuid import uuid4


class ModelError(ValueError):
    """Raised when task data or an operation is invalid."""


class MissingTaskError(ModelError):
    """Raised when a requested task does not exist."""


class DuplicateTaskError(ModelError):
    """Raised when a board receives a duplicate task identifier."""


class Status(str, Enum):
    TODO = "todo"
    ACTIVE = "active"
    DONE = "done"
    CANCELED = "canceled"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


TRANSITIONS = {
    Status.TODO: {Status.ACTIVE, Status.CANCELED},
    Status.ACTIVE: {Status.TODO, Status.DONE, Status.CANCELED},
    Status.DONE: {Status.TODO},
    Status.CANCELED: {Status.TODO},
}


@dataclass
class Task:
    """A validated task record with dates, labels, and lifecycle helpers."""

    title: str
    description: str = ""
    status: Status = Status.TODO
    priority: Priority = Priority.NORMAL
    due_date: Optional[date] = None
    tags: List[str] = field(default_factory=list)
    assignee: Optional[str] = None
    task_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if isinstance(self.title, str):
            self.title = self.title.strip()
        if isinstance(self.description, str):
            self.description = self.description.strip()
        self.status = self._enum(Status, self.status, "status")
        self.priority = self._enum(Priority, self.priority, "priority")
        self.tags = self._tags(self.tags)
        self.assignee = self._assignee(self.assignee)
        self.validate()

    @staticmethod
    def _enum(kind, value, name):
        if isinstance(value, kind):
            return value
        try:
            return kind(value)
        except (TypeError, ValueError) as error:
            options = ", ".join(item.value for item in kind)
            raise ModelError(f"{name} must be one of: {options}") from error

    @staticmethod
    def _tags(values: Iterable[str]) -> List[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, Iterable):
            raise ModelError("tags must be an iterable of strings")
        result = []
        for value in values:
            if not isinstance(value, str):
                raise ModelError("each tag must be a string")
            clean = value.strip().casefold()
            if clean and clean not in result:
                result.append(clean)
        return result

    @staticmethod
    def _assignee(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ModelError("assignee must be a string or None")
        clean = value.strip()
        return clean or None

    def validate(self) -> None:
        if not isinstance(self.title, str) or not self.title:
            raise ModelError("title is required")
        if len(self.title) > 160:
            raise ModelError("title must not exceed 160 characters")
        if not isinstance(self.description, str):
            raise ModelError("description must be a string")
        if len(self.description) > 5000:
            raise ModelError("description must not exceed 5000 characters")
        if self.due_date is not None and not isinstance(self.due_date, date):
            raise ModelError("due_date must be a date or None")
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise ModelError("task_id is required")
        if not isinstance(self.created_at, datetime):
            raise ModelError("created_at must be a datetime")
        if not isinstance(self.updated_at, datetime):
            raise ModelError("updated_at must be a datetime")
        if self.updated_at < self.created_at:
            raise ModelError("updated_at cannot precede created_at")

    def touch(self, timestamp: Optional[datetime] = None) -> None:
        timestamp = timestamp or datetime.now(timezone.utc)
        if timestamp < self.created_at:
            raise ModelError("update time cannot precede creation time")
        self.updated_at = timestamp

    def transition(self, status: Status) -> None:
        target = self._enum(Status, status, "status")
        if target == self.status:
            return
        if target not in TRANSITIONS[self.status]:
            raise ModelError(f"transition from {self.status.value} to {target.value} is not allowed")
        self.status = target
        self.touch()

    def is_active(self) -> bool:
        return self.status in {Status.TODO, Status.ACTIVE}

    def is_overdue(self, today: Optional[date] = None) -> bool:
        check_date = today or date.today()
        return bool(self.is_active() and self.due_date and self.due_date < check_date)

    def days_until_due(self, today: Optional[date] = None) -> Optional[int]:
        if self.due_date is None:
            return None
        return (self.due_date - (today or date.today())).days

    def add_tag(self, tag: str) -> None:
        additions = self._tags([tag])
        if additions and additions[0] not in self.tags:
            self.tags.append(additions[0])
            self.touch()

    def remove_tag(self, tag: str) -> bool:
        normalized = self._tags([tag])
        if not normalized or normalized[0] not in self.tags:
            return False
        self.tags.remove(normalized[0])
        self.touch()
        return True

    def assign(self, assignee: Optional[str]) -> None:
        normalized = self._assignee(assignee)
        if normalized != self.assignee:
            self.assignee = normalized
            self.touch()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "tags": list(self.tags),
            "assignee": self.assignee,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        if not isinstance(data, dict):
            raise ModelError("serialized task must be a dictionary")
        values = dict(data)
        if isinstance(values.get("due_date"), str):
            values["due_date"] = date.fromisoformat(values["due_date"])
        for key in ("created_at", "updated_at"):
            if isinstance(values.get(key), str):
                values[key] = datetime.fromisoformat(values[key])
        return cls(**values)


class TaskBoard:
    """An in-memory repository that offers task CRUD, queries, and JSON export."""

    def __init__(self, tasks: Optional[Iterable[Task]] = None) -> None:
        self._tasks: Dict[str, Task] = {}
        for task in tasks or []:
            self.add(task)

    def __len__(self) -> int:
        return len(self._tasks)

    def __contains__(self, task_id: str) -> bool:
        return task_id in self._tasks

    def __iter__(self):
        return iter(self.list_tasks())

    def add(self, task: Task) -> Task:
        if not isinstance(task, Task):
            raise ModelError("only Task objects can be added")
        if task.task_id in self._tasks:
            raise DuplicateTaskError(task.task_id)
        self._tasks[task.task_id] = task
        return task

    def create(self, title: str, **fields) -> Task:
        return self.add(Task(title=title, **fields))

    def get(self, task_id: str) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as error:
            raise MissingTaskError(task_id) from error

    def remove(self, task_id: str) -> Task:
        try:
            return self._tasks.pop(task_id)
        except KeyError as error:
            raise MissingTaskError(task_id) from error

    def update(self, task_id: str, **changes) -> Task:
        task = self.get(task_id)
        allowed = {"title", "description", "priority", "due_date", "tags", "assignee"}
        unknown = set(changes) - allowed
        if unknown:
            raise ModelError(f"unsupported fields: {', '.join(sorted(unknown))}")
        previous = task.to_dict()
        for key, value in changes.items():
            setattr(task, key, value)
        try:
            task.__post_init__()
            task.touch()
        except Exception:
            self._tasks[task_id] = Task.from_dict(previous)
            raise
        return task

    def list_tasks(
        self,
        status: Optional[Status] = None,
        priority: Optional[Priority] = None,
        assignee: Optional[str] = None,
        tag: Optional[str] = None,
        active_only: bool = False,
        overdue_on: Optional[date] = None,
    ) -> List[Task]:
        tasks = list(self._tasks.values())
        if status is not None:
            status = Task._enum(Status, status, "status")
            tasks = [task for task in tasks if task.status == status]
        if priority is not None:
            priority = Task._enum(Priority, priority, "priority")
            tasks = [task for task in tasks if task.priority == priority]
        if assignee is not None:
            target = assignee.strip().casefold()
            tasks = [task for task in tasks if task.assignee and task.assignee.casefold() == target]
        if tag is not None:
            target = tag.strip().casefold()
            tasks = [task for task in tasks if target in task.tags]
        if active_only:
            tasks = [task for task in tasks if task.is_active()]
        if overdue_on is not None:
            tasks = [task for task in tasks if task.is_overdue(overdue_on)]
        return sorted(tasks, key=lambda task: (task.created_at, task.task_id))

    def search(self, query: str) -> List[Task]:
        if not isinstance(query, str):
            raise ModelError("query must be a string")
        needle = query.strip().casefold()
        if not needle:
            return self.list_tasks()
        return [
            task for task in self.list_tasks()
            if needle in task.title.casefold() or needle in task.description.casefold()
        ]

    def due_date_order(self, include_undated: bool = False) -> List[Task]:
        dated = [task for task in self._tasks.values() if task.due_date is not None]
        undated = [task for task in self._tasks.values() if task.due_date is None]
        dated.sort(key=lambda task: (task.due_date, task.title.casefold()))
        if include_undated:
            dated.extend(sorted(undated, key=lambda task: task.title.casefold()))
        return dated

    def summary(self, today: Optional[date] = None) -> dict:
        by_status = {status.value: 0 for status in Status}
        for task in self._tasks.values():
            by_status[task.status.value] += 1
        return {
            "total": len(self),
            "active": sum(task.is_active() for task in self._tasks.values()),
            "overdue": sum(task.is_overdue(today) for task in self._tasks.values()),
            "by_status": by_status,
        }

    def export_json(self) -> str:
        return json.dumps([task.to_dict() for task in self.list_tasks()], sort_keys=True)

    @classmethod
    def import_json(cls, payload: str) -> "TaskBoard":
        try:
            records = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as error:
            raise ModelError("payload is not valid JSON") from error
        if not isinstance(records, list):
            raise ModelError("payload must be a list")
        return cls(Task.from_dict(record) for record in records)

    def clear(self) -> None:
        self._tasks.clear()

    def ids(self) -> tuple:
        return tuple(self._tasks)


class TaskModelTests(unittest.TestCase):
    def test_defaults_and_normalization(self):
        task = Task("  Write tests ", tags=[" Python ", "python"])
        self.assertEqual(task.title, "Write tests")
        self.assertEqual(task.status, Status.TODO)
        self.assertEqual(task.priority, Priority.NORMAL)
        self.assertEqual(task.tags, ["python"])

    def test_invalid_titles(self):
        for title in ("", " ", "\n", None, 7):
            with self.subTest(title=title):
                with self.assertRaises(ModelError):
                    Task(title)

    def test_unknown_status_or_priority(self):
        with self.assertRaises(ModelError):
            Task("x", status="waiting")
        with self.assertRaises(ModelError):
            Task("x", priority="critical")

    def test_tags_are_string_values(self):
        with self.assertRaises(ModelError):
            Task("x", tags=["valid", 8])

    def test_assignee_normalization_and_validation(self):
        self.assertEqual(Task("x", assignee=" Pat ").assignee, "Pat")
        self.assertIsNone(Task("x", assignee=" ").assignee)
        with self.assertRaises(ModelError):
            Task("x", assignee=3)

    def test_due_date_must_be_a_date(self):
        self.assertEqual(Task("x", due_date=date(2026, 2, 1)).due_date, date(2026, 2, 1))
        with self.assertRaises(ModelError):
            Task("x", due_date="2026-02-01")

    def test_allowed_transitions(self):
        task = Task("x")
        task.transition(Status.ACTIVE)
        task.transition(Status.DONE)
        task.transition(Status.TODO)
        self.assertEqual(task.status, Status.TODO)

    def test_active_and_overdue(self):
        task = Task("x", due_date=date(2026, 3, 1))
        self.assertTrue(task.is_active())
        self.assertTrue(task.is_overdue(date(2026, 3, 2)))
        task.transition(Status.ACTIVE)
        task.transition(Status.DONE)
        self.assertFalse(task.is_overdue(date(2026, 3, 2)))

    def test_tag_changes(self):
        task = Task("x", tags=["web"])
        task.add_tag(" PYTHON ")
        task.add_tag("web")
        self.assertEqual(task.tags, ["web", "python"])
        self.assertTrue(task.remove_tag("WEB"))
        self.assertFalse(task.remove_tag("missing"))

    def test_serialization_round_trip(self):
        task = Task("x", due_date=date(2026, 4, 3), tags=["daily"])
        restored = Task.from_dict(task.to_dict())
        self.assertEqual(restored.to_dict(), task.to_dict())


class TaskBoardTests(unittest.TestCase):
    def setUp(self):
        self.board = TaskBoard()
        self.first = self.board.create("Feature 01", tags=["web"], assignee="Pat")
        self.second = self.board.create(
            "Feature 02", priority=Priority.HIGH, description="Review the page"
        )
        self.third = self.board.create(
            "Feature 03", status=Status.ACTIVE, due_date=date(2026, 1, 1)
        )

    def test_reject_invalid_or_duplicate_additions(self):
        with self.assertRaises(ModelError):
            self.board.add("task")
        with self.assertRaises(DuplicateTaskError):
            self.board.add(Task("duplicate", task_id=self.first.task_id))

    def test_missing_task_errors(self):
        with self.assertRaises(MissingTaskError):
            self.board.get("missing")
        with self.assertRaises(MissingTaskError):
            self.board.remove("missing")

    def test_remove_and_membership(self):
        removed = self.board.remove(self.first.task_id)
        self.assertEqual(removed.title, "Feature 01")
        self.assertNotIn(removed.task_id, self.board)

    def test_update_allowed_fields(self):
        task = self.board.update(self.first.task_id, title="Renamed", priority="urgent")
        self.assertEqual(task.title, "Renamed")
        self.assertEqual(task.priority, Priority.URGENT)

    def test_update_rejects_unknown_fields(self):
        with self.assertRaises(ModelError):
            self.board.update(self.first.task_id, status=Status.DONE)

    def test_update_rolls_back_invalid_values(self):
        with self.assertRaises(ModelError):
            self.board.update(self.first.task_id, title=" ")
        self.assertEqual(self.board.get(self.first.task_id).title, "Feature 01")

    def test_status_filter(self):
        self.assertEqual(self.board.list_tasks(status="todo"), [self.first, self.second])

    def test_priority_assignee_and_tag_filters(self):
        self.assertEqual(self.board.list_tasks(priority="high"), [self.second])
        self.assertEqual(self.board.list_tasks(assignee="pat"), [self.first])
        self.assertEqual(self.board.list_tasks(tag="WEB"), [self.first])

    def test_active_and_overdue_filters(self):
        self.assertEqual(len(self.board.list_tasks(active_only=True)), 3)
        result = self.board.list_tasks(overdue_on=date(2026, 1, 2))
        self.assertEqual(result, [self.third])

    def test_search_is_case_insensitive(self):
        self.assertEqual(self.board.search("feature 01"), [self.first])
        self.assertEqual(self.board.search("page"), [self.second])

    def test_empty_search_returns_all(self):
        self.assertEqual(len(self.board.search(" ")), 3)

    def test_all_summary(self):
        summary = self.board.summary(today=date(2026, 1, 2))
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["active"], 3)
        self.assertEqual(summary["overdue"], 1)
        self.assertEqual(summary["by_status"]["todo"], 2)

    def test_due_date_order(self):
        result = self.board.due_date_order(include_undated=True)
        self.assertEqual(result[0], self.third)
        self.assertEqual(len(result), 3)

    def test_json_export_import(self):
        restored = TaskBoard.import_json(self.board.export_json())
        self.assertEqual(restored.export_json(), self.board.export_json())

    def test_invalid_json_and_non_list_payload(self):
        with self.assertRaises(ModelError):
            TaskBoard.import_json("{")
        with self.assertRaises(ModelError):
            TaskBoard.import_json("{}")

    def test_import_detects_duplicate_identifiers(self):
        records = [self.first.to_dict(), self.first.to_dict()]
        with self.assertRaises(DuplicateTaskError):
            TaskBoard.import_json(json.dumps(records))

    def test_clear_and_ids(self):
        self.assertEqual(len(self.board.ids()), 3)
        self.board.clear()
        self.assertEqual(len(self.board), 0)
        self.assertEqual(self.board.summary()["total"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
