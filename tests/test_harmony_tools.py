"""Unit tests for harmony tools."""

import pytest
from midi_gen_mcp.state import reset_state, get_state, undo_last_action, redo_last_action
from midi_gen_mcp.tools.harmony import add_chords, get_chords_in_range, remove_chords_in_range


def test_add_single_valid_chord():
    """Test adding a single valid chord."""
    reset_state()
    result = add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    assert result["success"] is True
    assert len(result["chords_added"]) == 1
    assert result["chords_added"][0]["chord"] == "C"
    assert result["chords_added"][0]["beat"] == 0
    assert result["chords_added"][0]["duration"] == 4
    assert "chord_tones" in result["chords_added"][0]
    assert len(result["errors"]) == 0


def test_add_multiple_valid_chords():
    """Test adding multiple valid chords."""
    reset_state()
    result = add_chords([
        {"beat": 0, "chord": "C", "duration": 4},
        {"beat": 4, "chord": "F", "duration": 4},
        {"beat": 8, "chord": "G7", "duration": 4}
    ])

    assert result["success"] is True
    assert len(result["chords_added"]) == 3
    assert len(result["errors"]) == 0

    state = get_state()
    assert len(state.chord_progression) == 3


def test_add_invalid_chord():
    """Test that invalid chord symbol returns error."""
    reset_state()
    result = add_chords([{"beat": 0, "chord": "InvalidChord", "duration": 4}])

    assert result["success"] is False
    assert len(result["errors"]) == 1
    assert "InvalidChord" in result["errors"][0]["invalid_chord"]

    # State should not be modified
    state = get_state()
    assert len(state.chord_progression) == 0


def test_add_mixed_valid_invalid():
    """Test adding mix of valid and invalid chords (should reject all)."""
    reset_state()
    result = add_chords([
        {"beat": 0, "chord": "C", "duration": 4},
        {"beat": 4, "chord": "InvalidChord", "duration": 4}
    ])

    assert result["success"] is False
    assert len(result["errors"]) >= 1

    # State should not be modified (atomic operation)
    state = get_state()
    assert len(state.chord_progression) == 0


def test_chord_overlap_splits_earlier_chord():
    """Test that overlapping chords split the earlier chord."""
    reset_state()

    # Add first chord from 0-8
    add_chords([{"beat": 0, "chord": "C", "duration": 8}])

    # Add second chord from 4-8 (overlaps)
    result = add_chords([{"beat": 4, "chord": "F", "duration": 4}])

    assert result["success"] is True

    state = get_state()
    # Should have 2 chords: C from 0-4, F from 4-8
    assert len(state.chord_progression) == 2

    # Find the C chord (should be split)
    c_chord = next(c for c in state.chord_progression if c["chord"] == "C")
    assert c_chord["beat"] == 0
    assert c_chord["duration"] == 4  # Split from 8 to 4

    # F chord should be intact
    f_chord = next(c for c in state.chord_progression if c["chord"] == "F")
    assert f_chord["beat"] == 4
    assert f_chord["duration"] == 4


def test_chord_overlap_complete_replacement():
    """Test that new chord completely replaces old chord."""
    reset_state()

    # Add first chord from 4-8
    add_chords([{"beat": 4, "chord": "C", "duration": 4}])

    # Add second chord from 0-12 (completely covers first)
    result = add_chords([{"beat": 0, "chord": "F", "duration": 12}])

    assert result["success"] is True

    state = get_state()
    # Should only have F chord
    assert len(state.chord_progression) == 1
    assert state.chord_progression[0]["chord"] == "F"


def test_chord_overlap_partial_both_sides():
    """Test chord that splits earlier chord on both sides."""
    reset_state()

    # Add first chord from 0-12
    add_chords([{"beat": 0, "chord": "C", "duration": 12}])

    # Add second chord from 4-8 (splits C into two parts)
    result = add_chords([{"beat": 4, "chord": "F", "duration": 4}])

    assert result["success"] is True

    state = get_state()
    # Should have 3 chords: C from 0-4, F from 4-8, C from 8-12
    assert len(state.chord_progression) == 3


def test_get_chords_in_range_normal():
    """Test getting chords in a normal range."""
    reset_state()
    add_chords([
        {"beat": 0, "chord": "C", "duration": 4},
        {"beat": 4, "chord": "F", "duration": 4},
        {"beat": 8, "chord": "G7", "duration": 4}
    ])

    result = get_chords_in_range(0, 8)

    # Should get C and F (not G7)
    assert len(result) == 2
    assert result[0]["chord"] == "C"
    assert result[1]["chord"] == "F"


def test_get_chords_in_range_empty():
    """Test getting chords when range is empty."""
    reset_state()
    add_chords([
        {"beat": 0, "chord": "C", "duration": 4},
        {"beat": 8, "chord": "G7", "duration": 4}
    ])

    result = get_chords_in_range(4, 8)

    # No chords in range 4-8
    assert len(result) == 0


def test_get_chords_in_range_partial_overlap():
    """Test getting chords with partial overlap."""
    reset_state()
    add_chords([
        {"beat": 0, "chord": "C", "duration": 6},
        {"beat": 10, "chord": "G7", "duration": 4}
    ])

    result = get_chords_in_range(4, 12)

    # Should get both chords (C overlaps, G7 is inside)
    assert len(result) == 2


def test_remove_chords_in_range():
    """Test removing chords in a range."""
    reset_state()
    add_chords([
        {"beat": 0, "chord": "C", "duration": 4},
        {"beat": 4, "chord": "F", "duration": 4},
        {"beat": 8, "chord": "G7", "duration": 4}
    ])

    result = remove_chords_in_range(4, 8)

    assert "Removed 1 chord(s)" in result

    state = get_state()
    # Should have C and G7 left
    assert len(state.chord_progression) == 2
    assert state.chord_progression[0]["chord"] == "C"
    assert state.chord_progression[1]["chord"] == "G7"


def test_remove_chords_clears_flags():
    """Test that removing chords clears all flagged notes."""
    reset_state()
    state = get_state()

    # Add some notes with flags
    state.notes = [
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1, "flagged": True},
        {"track": "piano", "pitch": 62, "start": 1, "duration": 1}
    ]

    add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    remove_chords_in_range(0, 4)

    # All flags should be cleared
    assert all("flagged" not in note for note in state.notes)


def test_undo_add_chords():
    """Test undoing chord additions."""
    reset_state()

    add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    state = get_state()
    assert len(state.chord_progression) == 1

    undo_last_action()

    state = get_state()
    assert len(state.chord_progression) == 0


def test_redo_add_chords():
    """Test redoing chord additions."""
    reset_state()

    add_chords([{"beat": 0, "chord": "C", "duration": 4}])
    undo_last_action()
    redo_last_action()

    state = get_state()
    assert len(state.chord_progression) == 1
    assert state.chord_progression[0]["chord"] == "C"


def test_chords_sorted_by_beat():
    """Test that chords are always sorted by beat."""
    reset_state()

    # Add chords out of order
    add_chords([
        {"beat": 8, "chord": "G7", "duration": 4},
        {"beat": 0, "chord": "C", "duration": 4},
        {"beat": 4, "chord": "F", "duration": 4}
    ])

    state = get_state()
    assert state.chord_progression[0]["beat"] == 0
    assert state.chord_progression[1]["beat"] == 4
    assert state.chord_progression[2]["beat"] == 8


def test_add_complex_jazz_chord():
    """Test adding complex jazz chord symbols."""
    reset_state()

    # Try some more complex chords
    result = add_chords([
        {"beat": 0, "chord": "Cmaj7", "duration": 4},
        {"beat": 4, "chord": "Dm7", "duration": 4},
        {"beat": 8, "chord": "G7", "duration": 4}
    ])

    assert result["success"] is True
    assert len(result["chords_added"]) == 3


def test_chord_tones_returned():
    """Test that chord tones are returned with each chord."""
    reset_state()

    result = add_chords([{"beat": 0, "chord": "C", "duration": 4}])

    assert "chord_tones" in result["chords_added"][0]
    chord_tones = result["chords_added"][0]["chord_tones"]
    assert "C" in chord_tones
    assert "E" in chord_tones
    assert "G" in chord_tones


def test_empty_chords_list():
    """Test adding empty chords list."""
    reset_state()

    result = add_chords([])

    assert result["success"] is True
    assert len(result["chords_added"]) == 0
    assert len(result["errors"]) == 0
