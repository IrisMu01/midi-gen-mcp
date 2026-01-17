"""Unit tests for validation tools."""

import pytest
from midi_gen_mcp.state import reset_state, get_state
from midi_gen_mcp.tools.track import add_track
from midi_gen_mcp.tools.harmony import add_chords
from midi_gen_mcp.tools.validation import flag_notes, remove_flagged_notes


def test_flag_notes_error_no_chord_progression():
    """Test that flag_notes returns error when no chord progression defined."""
    reset_state()
    add_track("piano", "piano")

    state = get_state()
    state.notes = [{"track": "piano", "pitch": 60, "start": 0, "duration": 1}]

    result = flag_notes(["piano"], 0, 4)

    assert "Error" in result["message"]
    assert "No chord progression" in result["message"]


def test_flag_notes_in_chord_not_flagged():
    """Test that notes matching the chord are not flagged."""
    reset_state()
    add_track("piano", "piano")

    # Add C major chord (C, E, G)
    add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    # Add notes that are in C major
    state = get_state()
    state.notes = [
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},  # C
        {"track": "piano", "pitch": 64, "start": 1, "duration": 1},  # E
        {"track": "piano", "pitch": 67, "start": 2, "duration": 1},  # G
    ]

    result = flag_notes(["piano"], 0, 4)

    assert result["flagged_count"] == 0
    # No notes should be flagged
    assert all("flagged" not in note for note in state.notes)


def test_flag_notes_outside_chord_flagged():
    """Test that notes outside the chord are flagged."""
    reset_state()
    add_track("piano", "piano")

    # Add C major chord (C, E, G)
    add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    # Add a note that's NOT in C major
    state = get_state()
    state.notes = [
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},  # C (in chord)
        {"track": "piano", "pitch": 61, "start": 1, "duration": 1},  # C# (NOT in chord)
    ]

    result = flag_notes(["piano"], 0, 4)

    assert result["flagged_count"] == 1
    # Only C# should be flagged
    assert state.notes[0].get("flagged") is None
    assert state.notes[1].get("flagged") is True


def test_flag_notes_multiple_tracks():
    """Test flagging notes across multiple tracks."""
    reset_state()
    add_track("piano", "piano")
    add_track("bass", "bass")

    # Add C major chord
    add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    state = get_state()
    state.notes = [
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},  # C (ok)
        {"track": "piano", "pitch": 61, "start": 1, "duration": 1},  # C# (flagged)
        {"track": "bass", "pitch": 48, "start": 0, "duration": 1},   # C (ok)
        {"track": "bass", "pitch": 49, "start": 1, "duration": 1},   # C# (flagged)
    ]

    result = flag_notes(["piano", "bass"], 0, 4)

    assert result["flagged_count"] == 2


def test_flag_notes_auto_clears_previous_flags():
    """Test that flag_notes auto-clears all previous flags."""
    reset_state()
    add_track("piano", "piano")

    add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    state = get_state()
    # Add notes with pre-existing flags
    state.notes = [
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1, "flagged": True},
        {"track": "piano", "pitch": 64, "start": 1, "duration": 1, "flagged": True},
    ]

    # Both notes are actually in the chord, so flags should be cleared
    result = flag_notes(["piano"], 0, 4)

    assert result["flagged_count"] == 0
    # All flags should be cleared
    assert all("flagged" not in note for note in state.notes)


def test_flag_notes_respects_track_filter():
    """Test that flag_notes only checks specified tracks."""
    reset_state()
    add_track("piano", "piano")
    add_track("bass", "bass")

    add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    state = get_state()
    state.notes = [
        {"track": "piano", "pitch": 61, "start": 0, "duration": 1},  # C# (should be flagged)
        {"track": "bass", "pitch": 49, "start": 0, "duration": 1},   # C# (should NOT be checked)
    ]

    # Only check piano track
    result = flag_notes(["piano"], 0, 4)

    assert result["flagged_count"] == 1
    assert state.notes[0].get("flagged") is True
    assert state.notes[1].get("flagged") is None


def test_flag_notes_respects_beat_range():
    """Test that flag_notes only checks notes in the specified range."""
    reset_state()
    add_track("piano", "piano")

    add_chords([{"beat": 0, "chord": "C", "duration": 8}])

    state = get_state()
    state.notes = [
        {"track": "piano", "pitch": 61, "start": 2, "duration": 1},  # In range (should be flagged)
        {"track": "piano", "pitch": 61, "start": 8, "duration": 1},  # Out of range (should NOT be checked)
    ]

    result = flag_notes(["piano"], 0, 4)

    assert result["flagged_count"] == 1
    assert state.notes[0].get("flagged") is True
    assert state.notes[1].get("flagged") is None


def test_flag_notes_missing_harmony_not_error():
    """Test that missing harmony (gaps in chords) doesn't flag notes."""
    reset_state()
    add_track("piano", "piano")

    # Add chords with gaps: C at 0-4, G at 8-12 (gap at 4-8)
    add_chords([
        {"beat": 0, "chord": "C", "duration": 4},
        {"beat": 8, "chord": "G", "duration": 4}
    ])

    state = get_state()
    state.notes = [
        {"track": "piano", "pitch": 60, "start": 6, "duration": 1},  # In gap - should NOT be flagged
    ]

    result = flag_notes(["piano"], 0, 12)

    # Note in gap should not be flagged (missing harmony is not an error)
    assert result["flagged_count"] == 0


def test_remove_flagged_notes():
    """Test removing flagged notes."""
    reset_state()
    add_track("piano", "piano")

    state = get_state()
    state.notes = [
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1, "flagged": True},
        {"track": "piano", "pitch": 62, "start": 1, "duration": 1},  # Not flagged
        {"track": "piano", "pitch": 64, "start": 2, "duration": 1, "flagged": True},
    ]

    result = remove_flagged_notes()

    assert result["count"] == 2
    assert len(result["removed_notes"]) == 2

    # Check that correct notes were removed
    assert result["removed_notes"][0]["pitch"] == 60
    assert result["removed_notes"][1]["pitch"] == 64

    # Only unflagged note should remain
    state = get_state()
    assert len(state.notes) == 1
    assert state.notes[0]["pitch"] == 62


def test_remove_flagged_notes_returns_correct_schema():
    """Test that removed notes have correct schema."""
    reset_state()
    add_track("piano", "piano")

    state = get_state()
    state.notes = [
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1, "flagged": True},
    ]

    result = remove_flagged_notes()

    removed = result["removed_notes"][0]
    assert "track" in removed
    assert "pitch" in removed
    assert "start" in removed
    assert "duration" in removed


def test_remove_flagged_notes_when_none_flagged():
    """Test removing flagged notes when there are none."""
    reset_state()
    add_track("piano", "piano")

    state = get_state()
    state.notes = [
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    ]

    result = remove_flagged_notes()

    assert result["count"] == 0
    assert len(result["removed_notes"]) == 0

    # All notes should remain
    state = get_state()
    assert len(state.notes) == 1


def test_integration_flag_remove_workflow():
    """Integration test: flag notes, remove them, verify."""
    reset_state()
    add_track("melody", "piano")

    # Add C major chord
    add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    state = get_state()
    # Add melody with some wrong notes
    state.notes = [
        {"track": "melody", "pitch": 60, "start": 0, "duration": 1},  # C (ok)
        {"track": "melody", "pitch": 61, "start": 1, "duration": 1},  # C# (wrong)
        {"track": "melody", "pitch": 64, "start": 2, "duration": 1},  # E (ok)
        {"track": "melody", "pitch": 66, "start": 3, "duration": 1},  # F# (wrong)
    ]

    # Flag wrong notes
    flag_result = flag_notes(["melody"], 0, 4)
    assert flag_result["flagged_count"] == 2

    # Remove flagged notes
    remove_result = remove_flagged_notes()
    assert remove_result["count"] == 2

    # Verify only correct notes remain
    state = get_state()
    assert len(state.notes) == 2
    assert state.notes[0]["pitch"] == 60  # C
    assert state.notes[1]["pitch"] == 64  # E


def test_enharmonic_equivalents():
    """Test that enharmonic equivalents are handled correctly."""
    reset_state()
    add_track("piano", "piano")

    # Add a chord that might use flats
    add_chords([{"beat": 0, "chord": "Db", "duration": 4}])

    state = get_state()
    # Add C# (enharmonic to Db)
    state.notes = [
        {"track": "piano", "pitch": 61, "start": 0, "duration": 1},  # C# = Db
    ]

    result = flag_notes(["piano"], 0, 4)

    # Should not be flagged because C# = Db
    assert result["flagged_count"] == 0
