"""Unit tests for chord parser module."""

import pytest
from midi_gen_mcp.chord_parser import parse_chord_symbol, get_supported_qualities


def test_parse_major_chord():
    """Test parsing a simple major chord."""
    result = parse_chord_symbol("C")
    assert result["chord"] == "C"
    assert "C" in result["chord_tones"]
    assert "E" in result["chord_tones"]
    assert "G" in result["chord_tones"]


def test_parse_minor_chord():
    """Test parsing a minor chord."""
    result = parse_chord_symbol("Cm")
    assert result["chord"] == "Cm"
    assert "C" in result["chord_tones"]
    # Minor third and fifth
    assert len(result["chord_tones"]) >= 3


def test_parse_dominant_7th():
    """Test parsing a dominant 7th chord."""
    result = parse_chord_symbol("G7")
    assert result["chord"] == "G7"
    assert "G" in result["chord_tones"]
    # Should have 4 notes (root, 3rd, 5th, 7th)
    assert len(result["chord_tones"]) == 4


def test_parse_major_7th():
    """Test parsing a major 7th chord."""
    result = parse_chord_symbol("Cmaj7")
    assert result["chord"] == "Cmaj7"
    assert "C" in result["chord_tones"]
    assert len(result["chord_tones"]) == 4


def test_parse_minor_7th():
    """Test parsing a minor 7th chord."""
    result = parse_chord_symbol("Dm7")
    assert result["chord"] == "Dm7"
    assert "D" in result["chord_tones"]
    assert len(result["chord_tones"]) == 4


def test_parse_diminished():
    """Test parsing a diminished chord."""
    result = parse_chord_symbol("Bdim")
    assert result["chord"] == "Bdim"
    assert "B" in result["chord_tones"]


def test_parse_augmented():
    """Test parsing an augmented chord."""
    result = parse_chord_symbol("Caug")
    assert result["chord"] == "Caug"
    assert "C" in result["chord_tones"]


def test_parse_sus4():
    """Test parsing a sus4 chord."""
    result = parse_chord_symbol("Dsus4")
    assert result["chord"] == "Dsus4"
    assert "D" in result["chord_tones"]


def test_parse_9th_chord():
    """Test parsing a 9th chord."""
    result = parse_chord_symbol("C9")
    assert result["chord"] == "C9"
    assert "C" in result["chord_tones"]
    # 9th chord has 5 notes
    assert len(result["chord_tones"]) == 5


def test_parse_add9():
    """Test parsing an add9 chord."""
    result = parse_chord_symbol("Cadd9")
    assert result["chord"] == "Cadd9"
    assert "C" in result["chord_tones"]


def test_parse_6th_chord():
    """Test parsing a 6th chord."""
    result = parse_chord_symbol("C6")
    assert result["chord"] == "C6"
    assert "C" in result["chord_tones"]


def test_parse_invalid_chord():
    """Test that invalid chord symbols raise ValueError."""
    with pytest.raises(ValueError) as excinfo:
        parse_chord_symbol("InvalidChord123")
    assert "Invalid chord symbol" in str(excinfo.value)
    assert "Supported qualities" in str(excinfo.value)


def test_parse_empty_string():
    """Test that empty string raises ValueError."""
    with pytest.raises(ValueError) as excinfo:
        parse_chord_symbol("")
    assert "Invalid chord symbol" in str(excinfo.value)


def test_get_supported_qualities():
    """Test getting list of supported qualities."""
    qualities = get_supported_qualities()
    assert isinstance(qualities, list)
    assert len(qualities) > 0
    # Check for some common qualities
    assert any("major" in q.lower() for q in qualities)
    assert any("minor" in q.lower() for q in qualities)


def test_sharp_chord():
    """Test parsing chord with sharp root."""
    result = parse_chord_symbol("F#")
    assert result["chord"] == "F#"
    assert "F#" in result["chord_tones"] or "Gb" in result["chord_tones"]


def test_flat_chord():
    """Test parsing chord with flat root."""
    result = parse_chord_symbol("Bb")
    assert result["chord"] == "Bb"
    assert "Bb" in result["chord_tones"] or "A#" in result["chord_tones"]
