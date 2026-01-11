"""Unit tests for state management."""

import pytest
from midi_gen_mcp.state import (
    get_state,
    reset_state,
    before_mutation,
    undo_last_action,
    redo_last_action,
)


def test_initial_state():
    """Test that initial state is empty."""
    reset_state()
    state = get_state()

    assert state.title == "Untitled"
    assert state.tracks == {}
    assert state.notes == []
    assert state.sections == []
    assert state.undo_stack == []
    assert state.redo_stack == []


def test_undo_with_empty_stack():
    """Test undo when there's nothing to undo."""
    reset_state()
    result = undo_last_action()
    assert result == "Nothing to undo"


def test_redo_with_empty_stack():
    """Test redo when there's nothing to redo."""
    reset_state()
    result = redo_last_action()
    assert result == "Nothing to redo"


def test_undo_redo_flow():
    """Test complete undo/redo flow."""
    reset_state()
    state = get_state()

    # Initial state
    state.title = "Original"

    # Make a change with snapshot
    before_mutation()
    state.title = "Changed"

    assert state.title == "Changed"
    assert len(state.undo_stack) == 1

    # Undo
    result = undo_last_action()
    assert result == "Undone"
    assert state.title == "Original"
    assert len(state.undo_stack) == 0
    assert len(state.redo_stack) == 1

    # Redo
    result = redo_last_action()
    assert result == "Redone"
    assert state.title == "Changed"
    assert len(state.undo_stack) == 1
    assert len(state.redo_stack) == 0


def test_new_action_clears_redo_stack():
    """Test that new action after undo clears redo stack."""
    reset_state()
    state = get_state()

    # Make changes
    state.title = "First"
    before_mutation()
    state.title = "Second"
    before_mutation()
    state.title = "Third"

    # Undo twice
    undo_last_action()
    undo_last_action()
    assert state.title == "First"
    assert len(state.redo_stack) == 2

    # Make a new change
    before_mutation()
    state.title = "New Branch"

    # Redo stack should be cleared
    assert len(state.redo_stack) == 0


def test_undo_stack_limit():
    """Test that undo stack is limited to 10 snapshots."""
    reset_state()
    state = get_state()

    # Make 15 changes
    for i in range(15):
        before_mutation()
        state.title = f"Change {i}"

    # Should only keep last 10
    assert len(state.undo_stack) == 10


def test_state_isolation():
    """Test that snapshots are deep copies (mutations don't affect history)."""
    reset_state()
    state = get_state()

    # Add a track
    state.tracks["piano"] = {"name": "piano", "instrument": "piano"}
    before_mutation()

    # Modify the track
    state.tracks["piano"]["instrument"] = "organ"

    # Undo should restore original
    undo_last_action()
    assert state.tracks["piano"]["instrument"] == "piano"


def test_undo_redo_with_sections():
    """Test undo/redo with section data."""
    reset_state()
    state = get_state()

    # Add a section
    section = {
        "name": "intro",
        "start_measure": 1,
        "end_measure": 4,
        "tempo": 120,
        "time_signature": "4/4",
        "key": "C",
        "description": "Opening section"
    }
    state.sections.append(section)

    before_mutation()

    # Modify section
    state.sections[0]["tempo"] = 140

    assert state.sections[0]["tempo"] == 140

    # Undo
    undo_last_action()
    assert state.sections[0]["tempo"] == 120
