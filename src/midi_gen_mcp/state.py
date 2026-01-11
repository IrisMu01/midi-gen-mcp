"""State management for the MCP server."""

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class State:
    """In-memory state for a single musical piece."""

    title: str = "Untitled"
    tracks: dict[str, dict[str, Any]] = field(default_factory=dict)
    notes: list[dict[str, Any]] = field(default_factory=list)
    sections: list[dict[str, Any]] = field(default_factory=list)
    undo_stack: list[dict[str, Any]] = field(default_factory=list)
    redo_stack: list[dict[str, Any]] = field(default_factory=list)


# Global state instance
_state = State()


def get_state() -> State:
    """Get the current state instance."""
    return _state


def reset_state() -> None:
    """Reset state to empty (useful for tests)."""
    global _state
    _state = State()


def snapshot_state() -> dict[str, Any]:
    """Create a deep copy of current state (excluding undo/redo stacks)."""
    return {
        'title': _state.title,
        'tracks': copy.deepcopy(_state.tracks),
        'notes': copy.deepcopy(_state.notes),
        'sections': copy.deepcopy(_state.sections),
    }


def restore_state(snapshot: dict[str, Any]) -> None:
    """Restore state from a snapshot."""
    _state.title = snapshot['title']
    _state.tracks = copy.deepcopy(snapshot['tracks'])
    _state.notes = copy.deepcopy(snapshot['notes'])
    _state.sections = copy.deepcopy(snapshot['sections'])


def before_mutation() -> None:
    """Call before ANY mutating operation to enable undo."""
    _state.undo_stack.append(snapshot_state())

    # Limit to 10 snapshots (memory management)
    if len(_state.undo_stack) > 10:
        _state.undo_stack.pop(0)

    # New action invalidates redo history
    _state.redo_stack.clear()


def undo_last_action() -> str:
    """Restore previous state."""
    if not _state.undo_stack:
        return "Nothing to undo"

    # Save current state to redo stack
    _state.redo_stack.append(snapshot_state())

    # Restore previous state
    previous = _state.undo_stack.pop()
    restore_state(previous)

    return "Undone"


def redo_last_action() -> str:
    """Restore undone state."""
    if not _state.redo_stack:
        return "Nothing to redo"

    # Save current state to undo stack
    _state.undo_stack.append(snapshot_state())

    # Restore redo state
    next_state = _state.redo_stack.pop()
    restore_state(next_state)

    return "Redone"
