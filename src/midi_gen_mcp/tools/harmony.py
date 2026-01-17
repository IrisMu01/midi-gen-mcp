"""Harmony/chord progression tools."""

from typing import List
from midi_gen_mcp.state import get_state, before_mutation
from midi_gen_mcp.chord_parser import parse_chord_symbol


def add_chords(chords: List[dict]) -> dict:
    """
    Add chord progression to the piece.

    Args:
        chords: List of {beat: float, chord: str, duration: float}

    Returns:
        {
            "success": bool,
            "chords_added": List[{beat, chord, duration, chord_tones}],
            "errors": List[{invalid_chord, error, supported_qualities}] (if any)
        }

    Behavior:
        - Validates each chord symbol using chord_parser
        - If all valid: adds to state.chord_progression, returns success
        - If any invalid: returns error with helpful message, state unchanged
        - Handles overlapping chords: later chord takes precedence, splits/removes earlier chords
    """
    state = get_state()
    errors = []
    parsed_chords = []

    # First, validate all chord symbols
    for chord_entry in chords:
        try:
            parsed = parse_chord_symbol(chord_entry["chord"])
            parsed_chords.append({
                "beat": chord_entry["beat"],
                "chord": chord_entry["chord"],
                "duration": chord_entry["duration"],
                "chord_tones": parsed["chord_tones"]
            })
        except ValueError as e:
            from midi_gen_mcp.chord_parser import get_supported_qualities
            errors.append({
                "invalid_chord": chord_entry["chord"],
                "error": str(e),
                "supported_qualities": get_supported_qualities()
            })

    # If any errors, return without modifying state
    if errors:
        return {
            "success": False,
            "chords_added": [],
            "errors": errors
        }

    # All valid - now add to state with overlap handling
    before_mutation()

    for new_chord in parsed_chords:
        new_start = new_chord["beat"]
        new_end = new_chord["beat"] + new_chord["duration"]

        # Remove or split overlapping chords
        updated_progression = []
        for existing_chord in state.chord_progression:
            existing_start = existing_chord["beat"]
            existing_end = existing_chord["beat"] + existing_chord["duration"]

            # No overlap - keep as is
            if existing_end <= new_start or existing_start >= new_end:
                updated_progression.append(existing_chord)
            # Partial overlap - split/trim the existing chord
            else:
                # Keep the part before the new chord
                if existing_start < new_start:
                    updated_progression.append({
                        "beat": existing_start,
                        "chord": existing_chord["chord"],
                        "duration": new_start - existing_start,
                        "chord_tones": existing_chord["chord_tones"]
                    })
                # Keep the part after the new chord
                if existing_end > new_end:
                    updated_progression.append({
                        "beat": new_end,
                        "chord": existing_chord["chord"],
                        "duration": existing_end - new_end,
                        "chord_tones": existing_chord["chord_tones"]
                    })

        state.chord_progression = updated_progression
        state.chord_progression.append(new_chord)

    # Sort by beat for consistency
    state.chord_progression.sort(key=lambda c: c["beat"])

    return {
        "success": True,
        "chords_added": parsed_chords,
        "errors": []
    }


def get_chords_in_range(start_beat: float, end_beat: float) -> List[dict]:
    """
    Get all chords in a beat range.

    Args:
        start_beat: Start of the range
        end_beat: End of the range

    Returns:
        List[{beat, chord, duration, chord_tones}]
    """
    state = get_state()
    chords_in_range = []

    for chord in state.chord_progression:
        chord_start = chord["beat"]
        chord_end = chord["beat"] + chord["duration"]

        # Check if chord overlaps with the range
        if chord_start < end_beat and chord_end > start_beat:
            chords_in_range.append(chord)

    return chords_in_range


def remove_chords_in_range(start_beat: float, end_beat: float) -> str:
    """
    Remove chords in a beat range.

    Args:
        start_beat: Start of the range
        end_beat: End of the range

    Side effects:
        - Clears ALL flagged notes (harmony context is now stale)

    Returns:
        Confirmation message
    """
    before_mutation()
    state = get_state()

    # Remove chords in range
    initial_count = len(state.chord_progression)
    state.chord_progression = [
        chord for chord in state.chord_progression
        if not (chord["beat"] < end_beat and
                chord["beat"] + chord["duration"] > start_beat)
    ]
    removed_count = initial_count - len(state.chord_progression)

    # Clear all flagged notes (harmony context is stale)
    for note in state.notes:
        note.pop("flagged", None)

    return f"Removed {removed_count} chord(s) in range [{start_beat}, {end_beat}). All note flags cleared."
