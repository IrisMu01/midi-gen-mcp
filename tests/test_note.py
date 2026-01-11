"""Tests for note operations."""

import pytest
from midi_gen_mcp.state import reset_state, get_state
from midi_gen_mcp.tools.track import add_track
from midi_gen_mcp.tools.note import add_notes, remove_notes_in_range, get_notes


@pytest.fixture(autouse=True)
def reset():
    """Reset state before each test."""
    reset_state()


def test_add_notes_simple():
    """Test adding simple notes."""
    add_track("piano", "piano")

    result = add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "piano", "pitch": 64, "start": 1, "duration": 1},
    ])

    assert "Added 2 note(s)" in result
    state = get_state()
    assert len(state.notes) == 2


def test_add_notes_with_expressions():
    """Test adding notes with expression syntax."""
    add_track("piano", "piano")

    result = add_notes([
        {"track": "piano", "pitch": 60, "start": "9 + 1/3", "duration": "1/3"},
        {"track": "piano", "pitch": 64, "start": "10 + 2/3", "duration": "1/3"},
    ])

    assert "Added 2 note(s)" in result
    state = get_state()
    assert len(state.notes) == 2

    # Check that expressions are stored as-is (not evaluated yet)
    assert state.notes[0]["start"] == "9 + 1/3"
    assert state.notes[0]["duration"] == "1/3"


def test_add_notes_missing_field():
    """Test adding notes with missing required field."""
    add_track("piano", "piano")

    result = add_notes([
        {"track": "piano", "pitch": 60, "start": 0},  # Missing duration
    ])

    assert "Error" in result
    assert "duration" in result


def test_add_notes_nonexistent_track():
    """Test adding notes to non-existent track."""
    result = add_notes([
        {"track": "nonexistent", "pitch": 60, "start": 0, "duration": 1},
    ])

    assert "Error" in result
    assert "not found" in result


def test_add_notes_invalid_pitch():
    """Test adding notes with invalid pitch."""
    add_track("piano", "piano")

    result = add_notes([
        {"track": "piano", "pitch": 200, "start": 0, "duration": 1},
    ])

    assert "Error" in result
    assert "Pitch" in result


def test_add_notes_invalid_expression():
    """Test adding notes with invalid expression."""
    add_track("piano", "piano")

    result = add_notes([
        {"track": "piano", "pitch": 60, "start": "invalid", "duration": 1},
    ])

    assert "Error" in result


def test_remove_notes_in_range():
    """Test removing notes in a time range."""
    add_track("piano", "piano")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "piano", "pitch": 64, "start": 1, "duration": 1},
        {"track": "piano", "pitch": 67, "start": 2, "duration": 1},
        {"track": "piano", "pitch": 72, "start": 3, "duration": 1},
    ])

    # Remove notes in range [1, 3)
    result = remove_notes_in_range("piano", 1, 3)

    assert "Removed 2 note(s)" in result

    state = get_state()
    assert len(state.notes) == 2

    # Check that the correct notes remain
    remaining_pitches = {n["pitch"] for n in state.notes}
    assert remaining_pitches == {60, 72}


def test_remove_notes_in_range_with_expressions():
    """Test removing notes that use expression syntax."""
    add_track("piano", "piano")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "piano", "pitch": 64, "start": "1 + 1/3", "duration": "1/3"},
        {"track": "piano", "pitch": 67, "start": 2, "duration": 1},
    ])

    # Remove notes in range [1, 2)
    result = remove_notes_in_range("piano", 1, 2)

    assert "Removed 1 note(s)" in result

    state = get_state()
    assert len(state.notes) == 2

    # Check that note with expression was removed
    remaining_pitches = {n["pitch"] for n in state.notes}
    assert remaining_pitches == {60, 67}


def test_remove_notes_in_range_empty():
    """Test removing notes from empty range."""
    add_track("piano", "piano")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    ])

    result = remove_notes_in_range("piano", 5, 10)

    assert "Removed 0 note(s)" in result

    state = get_state()
    assert len(state.notes) == 1


def test_remove_notes_nonexistent_track():
    """Test removing notes from non-existent track."""
    result = remove_notes_in_range("nonexistent", 0, 10)

    assert "Error" in result
    assert "not found" in result


def test_get_notes_all():
    """Test getting all notes."""
    add_track("piano", "piano")
    add_track("violin", "violin")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "violin", "pitch": 67, "start": 1, "duration": 1},
    ])

    notes = get_notes()

    assert len(notes) == 2


def test_get_notes_by_track():
    """Test getting notes filtered by track."""
    add_track("piano", "piano")
    add_track("violin", "violin")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "violin", "pitch": 67, "start": 1, "duration": 1},
        {"track": "piano", "pitch": 64, "start": 2, "duration": 1},
    ])

    piano_notes = get_notes(track="piano")

    assert len(piano_notes) == 2
    assert all(n["track"] == "piano" for n in piano_notes)


def test_get_notes_by_time_range():
    """Test getting notes filtered by time range."""
    add_track("piano", "piano")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "piano", "pitch": 64, "start": 1, "duration": 1},
        {"track": "piano", "pitch": 67, "start": 2, "duration": 1},
        {"track": "piano", "pitch": 72, "start": 3, "duration": 1},
    ])

    notes = get_notes(start_time=1, end_time=3)

    assert len(notes) == 2
    assert {n["pitch"] for n in notes} == {64, 67}


def test_get_notes_by_track_and_time():
    """Test getting notes filtered by both track and time."""
    add_track("piano", "piano")
    add_track("violin", "violin")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "violin", "pitch": 67, "start": 1, "duration": 1},
        {"track": "piano", "pitch": 64, "start": 2, "duration": 1},
        {"track": "violin", "pitch": 72, "start": 3, "duration": 1},
    ])

    notes = get_notes(track="piano", start_time=1, end_time=3)

    assert len(notes) == 1
    assert notes[0]["pitch"] == 64
    assert notes[0]["track"] == "piano"


def test_get_notes_with_expressions():
    """Test getting notes that use expression syntax."""
    add_track("piano", "piano")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "piano", "pitch": 64, "start": "1 + 1/3", "duration": "1/3"},
        {"track": "piano", "pitch": 67, "start": 2, "duration": 1},
    ])

    # Get notes in range [1, 2)
    notes = get_notes(start_time=1, end_time=2)

    assert len(notes) == 1
    assert notes[0]["pitch"] == 64


def test_get_notes_returns_copy():
    """Test that get_notes returns a copy (not modifiable)."""
    add_track("piano", "piano")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    ])

    notes = get_notes()
    notes[0]["pitch"] = 999

    # Verify original is unchanged
    state = get_state()
    assert state.notes[0]["pitch"] == 60


def test_notes_support_undo():
    """Test that note operations support undo."""
    add_track("piano", "piano")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    ])

    from midi_gen_mcp.state import undo_last_action

    undo_last_action()

    state = get_state()
    assert len(state.notes) == 0
