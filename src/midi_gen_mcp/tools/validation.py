"""Validation tools for checking melody against harmony."""

from typing import List
from midi_gen_mcp.state import get_state, before_mutation


# MIDI note number to pitch class mapping
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _midi_to_pitch_class(midi_note: int) -> str:
    """
    Convert MIDI note number to pitch class.

    Args:
        midi_note: MIDI note number (0-127)

    Returns:
        Pitch class string (e.g., "C", "C#", "D")
    """
    return PITCH_CLASSES[midi_note % 12]


def _eval_expression(value):
    """
    Evaluate a mathematical expression or numeric value to a float.

    Copied from note.py for consistency.
    """
    if isinstance(value, (int, float)):
        return float(value)

    try:
        result = eval(str(value), {"__builtins__": {}}, {})
        return float(result)
    except Exception as e:
        raise ValueError(f"Invalid expression '{value}': {e}")


def _find_chord_at_beat(beat: float) -> dict | None:
    """
    Find the active chord at a specific beat.

    Args:
        beat: The beat to check

    Returns:
        The chord dict if found, None otherwise
    """
    state = get_state()
    for chord in state.chord_progression:
        chord_start = chord["beat"]
        chord_end = chord["beat"] + chord["duration"]
        if chord_start <= beat < chord_end:
            return chord
    return None


def flag_notes(tracks: List[str], start_beat: float, end_beat: float) -> dict:
    """
    Flag notes that fall outside the planned chord progression.

    Args:
        tracks: Which tracks to check (e.g., ["piano", "bass"])
        start_beat: Start of the range
        end_beat: End of the range

    Returns:
        {
            "flagged_count": int,
            "message": str
        }

    Behavior:
        - Auto-clears ALL previous flags first
        - For each note in range:
          - Find active chord at note's start beat
          - If chord exists: check if note's pitch is in chord_tones
          - If not in chord_tones, set note["flagged"] = True
          - If no chord at that beat: don't flag (missing harmony is not an error)
        - Returns count of flagged notes

    Error handling:
        - If no chord_progression defined: return error
    """
    before_mutation()
    state = get_state()

    # Check if chord progression exists
    if not state.chord_progression:
        return {
            "flagged_count": 0,
            "message": "Error: No chord progression defined. Use add_chords first."
        }

    # Auto-clear ALL previous flags
    for note in state.notes:
        note.pop("flagged", None)

    flagged_count = 0

    # Check each note in the specified tracks and range
    for note in state.notes:
        # Skip if not in specified tracks
        if note.get("track") not in tracks:
            continue

        # Get note start beat
        try:
            note_start = _eval_expression(note.get("start", 0))
        except ValueError:
            continue  # Skip notes with invalid start times

        # Skip if not in range
        if note_start < start_beat or note_start >= end_beat:
            continue

        # Find active chord at this beat
        chord = _find_chord_at_beat(note_start)

        # If no chord at this beat, don't flag (missing harmony is not an error)
        if chord is None:
            continue

        # Check if note's pitch class is in chord tones
        pitch_class = _midi_to_pitch_class(note["pitch"])

        # Normalize chord tones for comparison (handle enharmonics)
        # pychord might return "Db" while our note is "C#", so we need to handle this
        chord_tones_normalized = set()
        for tone in chord["chord_tones"]:
            # Add both the tone itself and its enharmonic equivalent
            chord_tones_normalized.add(tone)
            # Add enharmonic equivalent
            if tone == "C#":
                chord_tones_normalized.add("Db")
            elif tone == "Db":
                chord_tones_normalized.add("C#")
            elif tone == "D#":
                chord_tones_normalized.add("Eb")
            elif tone == "Eb":
                chord_tones_normalized.add("D#")
            elif tone == "F#":
                chord_tones_normalized.add("Gb")
            elif tone == "Gb":
                chord_tones_normalized.add("F#")
            elif tone == "G#":
                chord_tones_normalized.add("Ab")
            elif tone == "Ab":
                chord_tones_normalized.add("G#")
            elif tone == "A#":
                chord_tones_normalized.add("Bb")
            elif tone == "Bb":
                chord_tones_normalized.add("A#")

        if pitch_class not in chord_tones_normalized:
            note["flagged"] = True
            flagged_count += 1

    return {
        "flagged_count": flagged_count,
        "message": f"Flagged {flagged_count} note(s) that don't match the chord progression."
    }


def remove_flagged_notes() -> dict:
    """
    Remove all flagged notes from state.

    Returns:
        {
            "removed_notes": List[{track, pitch, start, duration}],
            "count": int
        }

    Side effects:
        - Removes notes where flagged=True
        - No need to clear flagged field (notes are deleted)
    """
    before_mutation()
    state = get_state()

    # Collect flagged notes before removing
    flagged_notes = [
        {
            "track": note["track"],
            "pitch": note["pitch"],
            "start": note["start"],
            "duration": note["duration"]
        }
        for note in state.notes
        if note.get("flagged", False)
    ]

    # Remove flagged notes
    state.notes = [note for note in state.notes if not note.get("flagged", False)]

    return {
        "removed_notes": flagged_notes,
        "count": len(flagged_notes)
    }
