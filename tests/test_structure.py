"""Unit tests for structure management tools."""

import pytest
from midi_gen_mcp.state import reset_state, get_state
from midi_gen_mcp.tools.structure import add_section, edit_section, get_sections


def test_add_section():
    """Test adding a section."""
    reset_state()

    result = add_section(
        name="intro",
        start_measure=1,
        end_measure=4,
        tempo=120,
        time_signature="4/4",
        key="C",
        description="Opening section"
    )

    assert result == "Added section 'intro' (measures 1-4)"

    sections = get_sections()
    assert len(sections) == 1
    assert sections[0]["name"] == "intro"
    assert sections[0]["start_measure"] == 1
    assert sections[0]["end_measure"] == 4
    assert sections[0]["tempo"] == 120
    assert sections[0]["time_signature"] == "4/4"
    assert sections[0]["key"] == "C"
    assert sections[0]["description"] == "Opening section"


def test_add_multiple_sections_sorted():
    """Test that sections are sorted by start_measure."""
    reset_state()

    add_section("verse", 5, 12, 120, "4/4", "Am")
    add_section("intro", 1, 4, 120, "4/4", "C")
    add_section("chorus", 13, 20, 140, "4/4", "F")

    sections = get_sections()
    assert len(sections) == 3
    assert sections[0]["name"] == "intro"
    assert sections[1]["name"] == "verse"
    assert sections[2]["name"] == "chorus"


def test_add_section_duplicate_name():
    """Test that duplicate section names are rejected."""
    reset_state()

    add_section("intro", 1, 4, 120, "4/4", "C")
    result = add_section("intro", 5, 8, 120, "4/4", "G")

    assert "Error" in result
    assert "already exists" in result

    sections = get_sections()
    assert len(sections) == 1


def test_add_section_invalid_measures():
    """Test validation of measure numbers."""
    reset_state()

    # start_measure < 1
    result = add_section("bad1", 0, 4, 120, "4/4", "C")
    assert "Error" in result

    # end_measure < start_measure
    result = add_section("bad2", 5, 3, 120, "4/4", "C")
    assert "Error" in result

    sections = get_sections()
    assert len(sections) == 0


def test_edit_section_basic():
    """Test editing section fields."""
    reset_state()

    add_section("intro", 1, 4, 120, "4/4", "C", "Original description")

    result = edit_section(
        "intro",
        tempo=140,
        key="G",
        description="Updated description"
    )

    assert result == "Updated section 'intro'"

    sections = get_sections()
    assert sections[0]["tempo"] == 140
    assert sections[0]["key"] == "G"
    assert sections[0]["description"] == "Updated description"
    # Measures unchanged
    assert sections[0]["start_measure"] == 1
    assert sections[0]["end_measure"] == 4


def test_edit_section_not_found():
    """Test editing non-existent section."""
    reset_state()

    result = edit_section("nonexistent", tempo=120)
    assert "Error" in result
    assert "not found" in result


def test_edit_section_invalid_field():
    """Test editing with invalid field name."""
    reset_state()

    add_section("intro", 1, 4, 120, "4/4", "C")

    result = edit_section("intro", invalid_field="value")
    assert "Error" in result
    assert "Invalid field" in result


def test_neighbor_adjustment_expand_backward():
    """Test neighbor adjustment when expanding section backward."""
    reset_state()

    # Section A: 1-4, Section B: 5-12
    add_section("sectionA", 1, 4, 120, "4/4", "C")
    add_section("sectionB", 5, 12, 120, "4/4", "Am")

    # Expand sectionB backward to measure 3 (overlaps with sectionA)
    edit_section("sectionB", start_measure=3)

    sections = get_sections()

    # sectionA should be trimmed to end at measure 2
    assert sections[0]["name"] == "sectionA"
    assert sections[0]["end_measure"] == 2

    # sectionB should start at measure 3
    assert sections[1]["name"] == "sectionB"
    assert sections[1]["start_measure"] == 3


def test_neighbor_adjustment_expand_forward():
    """Test neighbor adjustment when expanding section forward."""
    reset_state()

    # Section A: 1-4, Section B: 5-12
    add_section("sectionA", 1, 4, 120, "4/4", "C")
    add_section("sectionB", 5, 12, 120, "4/4", "Am")

    # Expand sectionA forward to measure 7 (overlaps with sectionB)
    edit_section("sectionA", end_measure=7)

    sections = get_sections()

    # sectionA should end at measure 7
    assert sections[0]["name"] == "sectionA"
    assert sections[0]["end_measure"] == 7

    # sectionB should be trimmed to start at measure 8
    assert sections[1]["name"] == "sectionB"
    assert sections[1]["start_measure"] == 8


def test_neighbor_adjustment_remove_previous():
    """Test that previous section is removed if completely overlapped."""
    reset_state()

    # Section A: 1-4, Section B: 5-12
    add_section("sectionA", 1, 4, 120, "4/4", "C")
    add_section("sectionB", 5, 12, 120, "4/4", "Am")

    # Expand sectionB backward to measure 1 (completely overlaps sectionA)
    edit_section("sectionB", start_measure=1)

    sections = get_sections()

    # sectionA should be removed
    assert len(sections) == 1
    assert sections[0]["name"] == "sectionB"
    assert sections[0]["start_measure"] == 1


def test_neighbor_adjustment_remove_next():
    """Test that next section is removed if completely overlapped."""
    reset_state()

    # Section A: 1-4, Section B: 5-12
    add_section("sectionA", 1, 4, 120, "4/4", "C")
    add_section("sectionB", 5, 12, 120, "4/4", "Am")

    # Expand sectionA forward to measure 20 (completely overlaps sectionB)
    edit_section("sectionA", end_measure=20)

    sections = get_sections()

    # sectionB should be removed
    assert len(sections) == 1
    assert sections[0]["name"] == "sectionA"
    assert sections[0]["end_measure"] == 20


def test_neighbor_adjustment_three_sections():
    """Test neighbor adjustment with three sections."""
    reset_state()

    # Section A: 1-4, Section B: 5-12, Section C: 13-20
    add_section("sectionA", 1, 4, 120, "4/4", "C")
    add_section("sectionB", 5, 12, 120, "4/4", "Am")
    add_section("sectionC", 13, 20, 120, "4/4", "F")

    # Expand sectionB backward to measure 2
    edit_section("sectionB", start_measure=2)

    sections = get_sections()

    # sectionA should be trimmed
    assert sections[0]["name"] == "sectionA"
    assert sections[0]["end_measure"] == 1

    # sectionB should start at 2
    assert sections[1]["name"] == "sectionB"
    assert sections[1]["start_measure"] == 2

    # sectionC should be unchanged
    assert sections[2]["name"] == "sectionC"
    assert sections[2]["start_measure"] == 13
    assert sections[2]["end_measure"] == 20


def test_edit_section_with_undo():
    """Test that edit_section supports undo."""
    reset_state()
    from midi_gen_mcp.state import undo_last_action

    add_section("intro", 1, 4, 120, "4/4", "C")
    edit_section("intro", tempo=140)

    sections = get_sections()
    assert sections[0]["tempo"] == 140

    undo_last_action()
    sections = get_sections()
    assert sections[0]["tempo"] == 120


def test_get_sections_returns_copy():
    """Test that get_sections returns a copy, not reference."""
    reset_state()

    add_section("intro", 1, 4, 120, "4/4", "C")

    sections1 = get_sections()
    sections2 = get_sections()

    # Should be different lists
    assert sections1 is not sections2

    # Modifying one shouldn't affect the other
    sections1.append({"name": "fake"})
    assert len(sections2) == 1
