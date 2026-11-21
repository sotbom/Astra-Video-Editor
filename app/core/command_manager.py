"""Reversible metadata commands using structurally shared immutable project values."""

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from app.core.project_schema import Project, validate


@dataclass(frozen=True)
class EditCommand:
    label: str
    before: Project
    after: Project


class ProjectSession(QObject):
    changed = Signal()

    def __init__(self, project: Project | None = None, parent=None):
        super().__init__(parent)
        self.project = project or Project()
        self.saved = self.project
        self.undo_stack: list[EditCommand] = []
        self.redo_stack: list[EditCommand] = []

    @property
    def dirty(self) -> bool:
        return self.project != self.saved

    def execute(self, label: str, after: Project) -> None:
        """Validate before mutation; rejected edits never affect history or current state."""
        validate(after)
        if after == self.project:
            return
        self.undo_stack.append(EditCommand(label, self.project, after))
        self.undo_stack = self.undo_stack[-100:]
        self.redo_stack.clear()
        self.project = after
        self.changed.emit()

    def undo(self) -> None:
        if self.undo_stack:
            command = self.undo_stack.pop()
            self.redo_stack.append(command)
            self.project = command.before
            self.changed.emit()

    def redo(self) -> None:
        if self.redo_stack:
            command = self.redo_stack.pop()
            self.undo_stack.append(command)
            self.project = command.after
            self.changed.emit()

    def reset(self, project: Project, recovered: bool = False) -> None:
        validate(project)
        self.project = project
        self.saved = None if recovered else project
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.changed.emit()

    def mark_saved(self, snapshot: Project) -> None:
        """A completed async save marks only its captured snapshot as saved."""
        self.saved = snapshot
        self.changed.emit()
