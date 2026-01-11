"""Unit tests for track management tools."""

import pytest
from midi_gen_mcp.state import reset_state, get_state
from midi_gen_mcp.tools.track import add_track, remove_track, get_tracks


def test_add_track():
    """Test adding a track."""
    reset_state()

    result = add_track("piano", "piano")
    assert result == "Added track 'piano' (piano)"

    tracks = get_tracks()
    assert len(tracks) == 1
    assert "piano" in tracks
    assert tracks["piano"]["name"] == "piano"
    assert tracks["piano"]["instrument"] == "piano"


def test_add_multiple_tracks():
    """Test adding multiple tracks."""
    reset_state()

    add_track("piano", "piano")
    add_track("violin", "violin")
    add_track("drums", "drums")

    tracks = get_tracks()
    assert len(tracks) == 3
    assert set(tracks.keys()) == {"piano", "violin", "drums"}


def test_add_track_duplicate_name():
    """Test that duplicate track names are rejected."""
    reset_state()

    add_track("piano", "piano")
    result = add_track("piano", "organ")

    assert "Error" in result
    assert "already exists" in result

    tracks = get_tracks()
    assert len(tracks) == 1
    assert tracks["piano"]["instrument"] == "piano"  # Unchanged


def test_remove_track():
    """Test removing a track."""
    reset_state()

    add_track("piano", "piano")
    add_track("violin", "violin")

    result = remove_track("piano")
    assert "Removed track 'piano'" in result

    tracks = get_tracks()
    assert len(tracks) == 1
    assert "piano" not in tracks
    assert "violin" in tracks


def test_remove_track_not_found():
    """Test removing non-existent track."""
    reset_state()

    result = remove_track("nonexistent")
    assert "Error" in result
    assert "not found" in result


def test_remove_track_with_notes():
    """Test that removing track also removes its notes."""
    reset_state()
    state = get_state()

    # Add tracks
    add_track("piano", "piano")
    add_track("violin", "violin")

    # Add notes to both tracks
    state.notes.append({"track": "piano", "pitch": 60, "start": 0, "duration": 1})
    state.notes.append({"track": "piano", "pitch": 64, "start": 1, "duration": 1})
    state.notes.append({"track": "violin", "pitch": 67, "start": 0, "duration": 2})

    assert len(state.notes) == 3

    # Remove piano track
    result = remove_track("piano")
    assert "Removed track 'piano'" in result

    # Piano notes should be gone, violin notes remain
    assert len(state.notes) == 1
    assert state.notes[0]["track"] == "violin"


def test_add_track_with_undo():
    """Test that add_track supports undo."""
    reset_state()
    from midi_gen_mcp.state import undo_last_action

    add_track("piano", "piano")
    add_track("violin", "violin")

    tracks = get_tracks()
    assert len(tracks) == 2

    undo_last_action()
    tracks = get_tracks()
    assert len(tracks) == 1
    assert "piano" in tracks
    assert "violin" not in tracks


def test_remove_track_with_undo():
    """Test that remove_track supports undo."""
    reset_state()
    from midi_gen_mcp.state import undo_last_action
    state = get_state()

    # Add track with notes
    add_track("piano", "piano")
    state.notes.append({"track": "piano", "pitch": 60, "start": 0, "duration": 1})

    remove_track("piano")

    tracks = get_tracks()
    assert len(tracks) == 0
    assert len(state.notes) == 0

    # Undo removal
    undo_last_action()
    tracks = get_tracks()
    assert len(tracks) == 1
    assert "piano" in tracks
    assert len(state.notes) == 1


def test_get_tracks_returns_copy():
    """Test that get_tracks returns a copy, not reference."""
    reset_state()

    add_track("piano", "piano")

    tracks1 = get_tracks()
    tracks2 = get_tracks()

    # Should be different dicts
    assert tracks1 is not tracks2

    # Modifying one shouldn't affect the other
    tracks1["fake"] = {"name": "fake"}
    assert "fake" not in tracks2
