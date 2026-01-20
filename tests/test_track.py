"""Unit tests for track management tools."""

import pytest
from midi_gen_mcp.state import reset_state, get_state
from midi_gen_mcp.tools.track import add_track, edit_track, remove_track, get_tracks


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


# ============================================================================
# NEW FEATURE TESTS: Volume and Pan Support
# ============================================================================


def test_add_track_with_volume_and_pan():
    """Test adding a track with custom volume and pan values."""
    reset_state()

    result = add_track("piano", "piano", volume=50, pan=127)
    assert result == "Added track 'piano' (piano)"

    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 50
    assert tracks["piano"]["pan"] == 127


def test_add_track_volume_and_pan_defaults():
    """Test that volume and pan have default values."""
    reset_state()

    result = add_track("piano", "piano")
    assert result == "Added track 'piano' (piano)"

    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 100  # Default volume
    assert tracks["piano"]["pan"] == 64  # Default pan (center)


def test_add_track_volume_out_of_range():
    """Test that invalid volume values are rejected."""
    reset_state()

    # Test values below 0
    result = add_track("piano", "piano", volume=-10)
    assert "Error" in result
    assert "volume must be 0-127" in result

    # Test values above 127
    result = add_track("violin", "violin", volume=128)
    assert "Error" in result
    assert "volume must be 0-127" in result

    result = add_track("bass", "bass", volume=200)
    assert "Error" in result
    assert "volume must be 0-127" in result

    # No tracks should have been created
    tracks = get_tracks()
    assert len(tracks) == 0


def test_add_track_pan_out_of_range():
    """Test that invalid pan values are rejected."""
    reset_state()

    # Test values below 0
    result = add_track("piano", "piano", pan=-1)
    assert "Error" in result
    assert "pan must be 0-127" in result

    # Test values above 127
    result = add_track("violin", "violin", pan=128)
    assert "Error" in result
    assert "pan must be 0-127" in result

    result = add_track("bass", "bass", pan=300)
    assert "Error" in result
    assert "pan must be 0-127" in result

    # No tracks should have been created
    tracks = get_tracks()
    assert len(tracks) == 0


def test_add_track_volume_and_pan_boundary_values():
    """Test boundary values for volume and pan (0, 127)."""
    reset_state()

    # Test minimum values
    result1 = add_track("piano", "piano", volume=0, pan=0)
    assert "Added track 'piano'" in result1

    # Test maximum values
    result2 = add_track("violin", "violin", volume=127, pan=127)
    assert "Added track 'violin'" in result2

    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 0
    assert tracks["piano"]["pan"] == 0
    assert tracks["violin"]["volume"] == 127
    assert tracks["violin"]["pan"] == 127


def test_add_track_with_volume_pan_undo():
    """Test that adding track with volume/pan supports undo."""
    reset_state()
    from midi_gen_mcp.state import undo_last_action

    add_track("piano", "piano", volume=50, pan=127)

    tracks = get_tracks()
    assert len(tracks) == 1
    assert tracks["piano"]["volume"] == 50
    assert tracks["piano"]["pan"] == 127

    undo_last_action()
    tracks = get_tracks()
    assert len(tracks) == 0


def test_add_track_with_volume_pan_redo():
    """Test that adding track with volume/pan supports redo."""
    reset_state()
    from midi_gen_mcp.state import undo_last_action, redo_last_action

    add_track("piano", "piano", volume=50, pan=127)
    undo_last_action()

    tracks = get_tracks()
    assert len(tracks) == 0

    redo_last_action()
    tracks = get_tracks()
    assert len(tracks) == 1
    assert tracks["piano"]["volume"] == 50
    assert tracks["piano"]["pan"] == 127


# ============================================================================
# EDIT TRACK TESTS
# ============================================================================


def test_edit_track_volume():
    """Test editing track volume."""
    reset_state()

    add_track("piano", "piano", volume=100, pan=64)
    result = edit_track("piano", volume=50)

    assert "Updated track 'piano'" in result
    assert "volume=50" in result

    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 50
    assert tracks["piano"]["pan"] == 64  # Unchanged


def test_edit_track_pan():
    """Test editing track pan."""
    reset_state()

    add_track("piano", "piano", volume=100, pan=64)
    result = edit_track("piano", pan=127)

    assert "Updated track 'piano'" in result
    assert "pan=127" in result

    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 100  # Unchanged
    assert tracks["piano"]["pan"] == 127


def test_edit_track_both():
    """Test editing both volume and pan."""
    reset_state()

    add_track("piano", "piano", volume=100, pan=64)
    result = edit_track("piano", volume=75, pan=0)

    assert "Updated track 'piano'" in result
    assert "volume=75" in result
    assert "pan=0" in result

    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 75
    assert tracks["piano"]["pan"] == 0


def test_edit_track_not_found():
    """Test editing non-existent track."""
    reset_state()

    result = edit_track("nonexistent", volume=50)
    assert "Error" in result
    assert "not found" in result


def test_edit_track_no_params():
    """Test editing track with no parameters."""
    reset_state()

    add_track("piano", "piano")
    result = edit_track("piano")

    assert "Error" in result
    assert "Must specify at least one" in result


def test_edit_track_volume_out_of_range():
    """Test editing track with invalid volume."""
    reset_state()

    add_track("piano", "piano")

    # Test below 0
    result = edit_track("piano", volume=-1)
    assert "Error" in result
    assert "volume must be 0-127" in result

    # Test above 127
    result = edit_track("piano", volume=128)
    assert "Error" in result
    assert "volume must be 0-127" in result


def test_edit_track_pan_out_of_range():
    """Test editing track with invalid pan."""
    reset_state()

    add_track("piano", "piano")

    # Test below 0
    result = edit_track("piano", pan=-1)
    assert "Error" in result
    assert "pan must be 0-127" in result

    # Test above 127
    result = edit_track("piano", pan=128)
    assert "Error" in result
    assert "pan must be 0-127" in result


def test_edit_track_preserves_notes():
    """Test that editing track doesn't affect notes."""
    reset_state()
    state = get_state()

    add_track("piano", "piano")
    state.notes.append({"track": "piano", "pitch": 60, "start": 0, "duration": 1})
    state.notes.append({"track": "piano", "pitch": 64, "start": 1, "duration": 1})

    assert len(state.notes) == 2

    result = edit_track("piano", volume=50)
    assert "Updated" in result

    # Notes should still be there
    assert len(state.notes) == 2
    assert all(n["track"] == "piano" for n in state.notes)


def test_edit_track_with_undo():
    """Test that editing track supports undo."""
    reset_state()
    from midi_gen_mcp.state import undo_last_action

    add_track("piano", "piano", volume=100, pan=64)
    edit_track("piano", volume=50, pan=127)

    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 50
    assert tracks["piano"]["pan"] == 127

    undo_last_action()
    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 100
    assert tracks["piano"]["pan"] == 64


def test_edit_track_with_redo():
    """Test that editing track supports redo."""
    reset_state()
    from midi_gen_mcp.state import undo_last_action, redo_last_action

    add_track("piano", "piano", volume=100, pan=64)
    edit_track("piano", volume=50, pan=127)
    undo_last_action()

    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 100

    redo_last_action()
    tracks = get_tracks()
    assert tracks["piano"]["volume"] == 50
    assert tracks["piano"]["pan"] == 127
