"""Unit tests for song management tools."""

import pytest
from midi_gen_mcp.state import reset_state, get_state
from midi_gen_mcp.tools.song import set_title, get_piece_info


def test_set_title():
    """Test setting piece title."""
    reset_state()

    result = set_title("Moonlight Sonata")
    assert result == "Title set to: Moonlight Sonata"

    state = get_state()
    assert state.title == "Moonlight Sonata"


def test_set_title_with_undo():
    """Test that set_title supports undo."""
    reset_state()
    from midi_gen_mcp.state import undo_last_action

    set_title("First Title")
    set_title("Second Title")

    state = get_state()
    assert state.title == "Second Title"
    assert len(state.undo_stack) == 2

    undo_last_action()
    assert state.title == "First Title"


def test_get_piece_info_empty():
    """Test getting piece info when empty."""
    reset_state()

    info = get_piece_info()
    assert info["title"] == "Untitled"
    assert info["num_sections"] == 0
    assert info["num_tracks"] == 0
    assert info["num_notes"] == 0
    assert info["sections"] == []
    assert info["tracks"] == []


def test_get_piece_info_with_data():
    """Test getting piece info with sections and tracks."""
    reset_state()
    state = get_state()

    # Set title
    set_title("Test Piece")

    # Add sections
    state.sections.append({
        "name": "intro",
        "start_measure": 1,
        "end_measure": 4,
        "tempo": 120,
        "time_signature": "4/4",
        "key": "C",
        "description": "Opening"
    })
    state.sections.append({
        "name": "verse",
        "start_measure": 5,
        "end_measure": 12,
        "tempo": 120,
        "time_signature": "4/4",
        "key": "Am",
        "description": "Main theme"
    })

    # Add tracks
    state.tracks["piano"] = {"name": "piano", "instrument": "piano"}
    state.tracks["strings"] = {"name": "strings", "instrument": "strings"}

    # Get info
    info = get_piece_info()

    assert info["title"] == "Test Piece"
    assert info["num_sections"] == 2
    assert info["num_tracks"] == 2
    assert info["num_notes"] == 0

    assert len(info["sections"]) == 2
    assert info["sections"][0]["name"] == "intro"
    assert info["sections"][0]["measures"] == "1-4"
    assert info["sections"][0]["tempo"] == 120
    assert info["sections"][0]["time_signature"] == "4/4"
    assert info["sections"][0]["key"] == "C"

    assert info["sections"][1]["name"] == "verse"
    assert info["sections"][1]["key"] == "Am"

    assert set(info["tracks"]) == {"piano", "strings"}
