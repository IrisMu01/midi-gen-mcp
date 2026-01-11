"""Tests for MIDI export."""

import os
import pytest
import mido
from midi_gen_mcp.state import reset_state, get_state
from midi_gen_mcp.tools.track import add_track
from midi_gen_mcp.tools.note import add_notes
from midi_gen_mcp.tools.structure import add_section
from midi_gen_mcp.tools.song import set_title
from midi_gen_mcp.midi_export import export_midi, _eval_expression, _get_instrument_program, _beats_to_ticks


@pytest.fixture(autouse=True)
def reset():
    """Reset state before each test."""
    reset_state()


@pytest.fixture
def temp_midi_file(tmp_path):
    """Provide a temporary MIDI file path."""
    return str(tmp_path / "test.mid")


def test_eval_expression_numbers():
    """Test expression evaluation with numbers."""
    assert _eval_expression(5) == 5.0
    assert _eval_expression(3.14) == 3.14
    assert _eval_expression(0) == 0.0


def test_eval_expression_simple():
    """Test simple expression evaluation."""
    assert _eval_expression("1/3") == pytest.approx(0.333333, rel=1e-5)
    assert _eval_expression("1/2") == 0.5
    assert _eval_expression("3/4") == 0.75


def test_eval_expression_complex():
    """Test complex expression evaluation."""
    assert _eval_expression("9 + 1/3") == pytest.approx(9.333333, rel=1e-5)
    assert _eval_expression("2 * 3") == 6.0
    assert _eval_expression("10 - 2.5") == 7.5


def test_eval_expression_invalid():
    """Test invalid expression evaluation."""
    with pytest.raises(ValueError):
        _eval_expression("invalid")

    with pytest.raises(ValueError):
        _eval_expression("1 + ")


def test_get_instrument_program_common():
    """Test instrument program lookup for common instruments."""
    assert _get_instrument_program("piano") == 0
    assert _get_instrument_program("violin") == 40
    assert _get_instrument_program("trumpet") == 56
    assert _get_instrument_program("flute") == 73


def test_get_instrument_program_case_insensitive():
    """Test instrument lookup is case-insensitive."""
    assert _get_instrument_program("PIANO") == 0
    assert _get_instrument_program("Piano") == 0
    assert _get_instrument_program("pIaNo") == 0


def test_get_instrument_program_spaces():
    """Test instrument lookup handles spaces."""
    assert _get_instrument_program("acoustic guitar nylon") == 24
    assert _get_instrument_program("electric bass finger") == 33


def test_get_instrument_program_unknown():
    """Test unknown instrument defaults to piano."""
    assert _get_instrument_program("unknown_instrument") == 0
    assert _get_instrument_program("???") == 0


def test_beats_to_ticks():
    """Test beat to tick conversion."""
    assert _beats_to_ticks(1) == 480  # 1 quarter note = 480 ticks
    assert _beats_to_ticks(2) == 960
    assert _beats_to_ticks(0.5) == 240  # Half quarter note
    assert _beats_to_ticks(0.25) == 120  # Quarter of quarter note


def test_export_midi_simple(temp_midi_file):
    """Test exporting a simple MIDI file."""
    set_title("Test Song")
    add_track("piano", "piano")
    add_section("intro", 1, 4, 120, "4/4", "C", "Test section")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "piano", "pitch": 64, "start": 1, "duration": 1},
        {"track": "piano", "pitch": 67, "start": 2, "duration": 1},
    ])

    result = export_midi(temp_midi_file)

    assert "Exported MIDI" in result
    assert "1 tracks" in result
    assert "3 notes" in result
    assert os.path.exists(temp_midi_file)

    # Verify MIDI file structure
    midi = mido.MidiFile(temp_midi_file)
    assert len(midi.tracks) == 1

    # Check that notes are present
    note_on_messages = [msg for msg in midi.tracks[0] if msg.type == "note_on"]
    assert len(note_on_messages) == 3


def test_export_midi_with_expressions(temp_midi_file):
    """Test exporting MIDI with expression syntax in notes."""
    add_track("piano", "piano")
    add_section("intro", 1, 4, 120, "4/4", "C")

    add_notes([
        {"track": "piano", "pitch": 60, "start": "9 + 1/3", "duration": "1/3"},
        {"track": "piano", "pitch": 64, "start": "10", "duration": "1/2"},
    ])

    result = export_midi(temp_midi_file)

    assert "Exported MIDI" in result
    assert os.path.exists(temp_midi_file)

    # Verify file is valid
    midi = mido.MidiFile(temp_midi_file)
    assert len(midi.tracks) == 1


def test_export_midi_multiple_tracks(temp_midi_file):
    """Test exporting MIDI with multiple tracks."""
    add_track("piano", "piano")
    add_track("violin", "violin")
    add_track("bass", "bass")
    add_section("intro", 1, 4, 120, "4/4", "C")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "violin", "pitch": 67, "start": 0, "duration": 1},
        {"track": "bass", "pitch": 48, "start": 0, "duration": 2},
    ])

    result = export_midi(temp_midi_file)

    assert "3 tracks" in result
    assert os.path.exists(temp_midi_file)

    # Verify MIDI file has 3 tracks
    midi = mido.MidiFile(temp_midi_file)
    assert len(midi.tracks) == 3


def test_export_midi_drums_on_channel_9(temp_midi_file):
    """Test that drums are assigned to channel 9 (percussion channel)."""
    add_track("drums", "drums")
    add_track("piano", "piano")
    add_section("intro", 1, 4, 120, "4/4", "C")

    add_notes([
        {"track": "drums", "pitch": 36, "start": 0, "duration": 0.5},
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    ])

    result = export_midi(temp_midi_file)

    assert os.path.exists(temp_midi_file)

    # Check that drums use channel 9
    midi = mido.MidiFile(temp_midi_file)
    for track in midi.tracks:
        for msg in track:
            if msg.type == "note_on":
                # Find the track by checking track name
                track_name_msgs = [m for m in track if m.type == "track_name"]
                if track_name_msgs and track_name_msgs[0].name == "drums":
                    assert msg.channel == 9


def test_export_midi_tempo_from_section(temp_midi_file):
    """Test that tempo is read from section."""
    add_track("piano", "piano")
    add_section("intro", 1, 4, 140, "4/4", "C")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    ])

    result = export_midi(temp_midi_file)

    assert os.path.exists(temp_midi_file)

    # Check tempo meta message
    midi = mido.MidiFile(temp_midi_file)
    tempo_msgs = [msg for msg in midi.tracks[0] if msg.type == "set_tempo"]
    assert len(tempo_msgs) > 0

    # Verify tempo (140 BPM = 428571 microseconds per beat)
    expected_tempo = int(60_000_000 / 140)
    assert tempo_msgs[0].tempo == expected_tempo


def test_export_midi_time_signature_from_section(temp_midi_file):
    """Test that time signature is read from section."""
    add_track("piano", "piano")
    add_section("intro", 1, 4, 120, "6/8", "C")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    ])

    result = export_midi(temp_midi_file)

    assert os.path.exists(temp_midi_file)

    # Check time signature meta message
    midi = mido.MidiFile(temp_midi_file)
    time_sig_msgs = [msg for msg in midi.tracks[0] if msg.type == "time_signature"]
    assert len(time_sig_msgs) > 0
    assert time_sig_msgs[0].numerator == 6
    assert time_sig_msgs[0].denominator == 8


def test_export_midi_adds_extension(tmp_path):
    """Test that .mid extension is added if missing."""
    filepath = str(tmp_path / "test")  # No extension

    add_track("piano", "piano")
    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    ])

    result = export_midi(filepath)

    assert "Exported MIDI" in result
    assert os.path.exists(filepath + ".mid")


def test_export_midi_empty_piece(temp_midi_file):
    """Test exporting an empty piece."""
    result = export_midi(temp_midi_file)

    assert "Exported MIDI" in result
    assert "0 tracks" in result
    assert "0 notes" in result
    assert os.path.exists(temp_midi_file)


def test_export_midi_default_tempo_and_time_sig(temp_midi_file):
    """Test that defaults are used when no sections exist."""
    add_track("piano", "piano")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    ])

    result = export_midi(temp_midi_file)

    assert os.path.exists(temp_midi_file)

    midi = mido.MidiFile(temp_midi_file)

    # Check default tempo (120 BPM)
    tempo_msgs = [msg for msg in midi.tracks[0] if msg.type == "set_tempo"]
    if tempo_msgs:
        expected_tempo = int(60_000_000 / 120)
        assert tempo_msgs[0].tempo == expected_tempo

    # Check default time signature (4/4)
    time_sig_msgs = [msg for msg in midi.tracks[0] if msg.type == "time_signature"]
    if time_sig_msgs:
        assert time_sig_msgs[0].numerator == 4
        assert time_sig_msgs[0].denominator == 4


def test_export_midi_channel_assignment(temp_midi_file):
    """Test that tracks are assigned different MIDI channels."""
    add_track("piano", "piano")
    add_track("violin", "violin")
    add_track("bass", "bass")
    add_section("intro", 1, 4, 120, "4/4", "C")

    add_notes([
        {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        {"track": "violin", "pitch": 67, "start": 0, "duration": 1},
        {"track": "bass", "pitch": 48, "start": 0, "duration": 1},
    ])

    result = export_midi(temp_midi_file)

    assert os.path.exists(temp_midi_file)

    midi = mido.MidiFile(temp_midi_file)
    channels_used = set()

    for track in midi.tracks:
        for msg in track:
            if msg.type in ["note_on", "note_off"]:
                channels_used.add(msg.channel)

    # All three tracks should use different channels
    assert len(channels_used) == 3


def test_export_midi_program_change(temp_midi_file):
    """Test that program change messages are added for instruments."""
    add_track("violin", "violin")
    add_section("intro", 1, 4, 120, "4/4", "C")

    add_notes([
        {"track": "violin", "pitch": 67, "start": 0, "duration": 1},
    ])

    result = export_midi(temp_midi_file)

    assert os.path.exists(temp_midi_file)

    midi = mido.MidiFile(temp_midi_file)

    # Check for program change message
    program_msgs = [msg for msg in midi.tracks[0] if msg.type == "program_change"]
    assert len(program_msgs) > 0
    assert program_msgs[0].program == 40  # Violin
