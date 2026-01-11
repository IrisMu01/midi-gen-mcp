"""Note management tools."""

from typing import List, Union, Optional
from midi_gen_mcp.state import get_state, before_mutation


def _eval_expression(value: Union[str, int, float]) -> float:
    """
    Evaluate a mathematical expression or numeric value to a float.

    Supports expressions like "9 + 1/3" or simple numbers.

    Args:
        value: Either a number or a string expression

    Returns:
        The evaluated result as a float

    Examples:
        >>> _eval_expression(9)
        9.0
        >>> _eval_expression("9 + 1/3")
        9.333333...
        >>> _eval_expression("1/3")
        0.333333...
    """
    if isinstance(value, (int, float)):
        return float(value)

    # Evaluate the string expression safely
    # Only allow basic arithmetic operations
    try:
        # Use eval with restricted namespace for safety
        result = eval(str(value), {"__builtins__": {}}, {})
        return float(result)
    except Exception as e:
        raise ValueError(f"Invalid expression '{value}': {e}")


def add_notes(notes: List[dict]) -> str:
    """
    Add multiple notes to the piece (batch operation).

    Args:
        notes: List of note dictionaries with fields:
            - track (str): Track name (must exist)
            - pitch (int): MIDI note number (0-127)
            - start (str/float): Start time in beats (quarter notes)
            - duration (str/float): Duration in beats

    Returns:
        Confirmation message

    Examples:
        >>> add_notes([
        ...     {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
        ...     {"track": "piano", "pitch": 64, "start": "1/3", "duration": "1/3"}
        ... ])
    """
    before_mutation()
    state = get_state()

    # Validate all notes before adding any
    for note in notes:
        # Check required fields
        required_fields = ["track", "pitch", "start", "duration"]
        for field in required_fields:
            if field not in note:
                return f"Error: Note missing required field '{field}'"

        # Check track exists
        if note["track"] not in state.tracks:
            return f"Error: Track '{note['track']}' not found"

        # Validate pitch
        if not isinstance(note["pitch"], int) or not (0 <= note["pitch"] <= 127):
            return f"Error: Pitch must be an integer between 0-127, got {note['pitch']}"

        # Validate that start and duration can be evaluated
        try:
            _eval_expression(note["start"])
            _eval_expression(note["duration"])
        except ValueError as e:
            return f"Error: {e}"

    # Add all notes
    state.notes.extend(notes)

    return f"Added {len(notes)} note(s)"


def remove_notes_in_range(
    track: str,
    start_time: float,
    end_time: float
) -> str:
    """
    Remove all notes in a track within a time range.

    Args:
        track: Track name
        start_time: Start time in beats (inclusive)
        end_time: End time in beats (exclusive)

    Returns:
        Confirmation message with count of removed notes

    Note:
        A note is considered in range if its start time is >= start_time
        and < end_time.
    """
    before_mutation()
    state = get_state()

    # Check track exists
    if track not in state.tracks:
        return f"Error: Track '{track}' not found"

    # Count notes before removal
    initial_count = len(state.notes)

    # Filter out notes in range
    state.notes = [
        n for n in state.notes
        if not (
            n.get("track") == track and
            start_time <= _eval_expression(n.get("start", 0)) < end_time
        )
    ]

    removed_count = initial_count - len(state.notes)

    return f"Removed {removed_count} note(s) from '{track}' in range [{start_time}, {end_time})"


def get_notes(
    track: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> List[dict]:
    """
    Query notes, optionally filtered by track and/or time range.

    Args:
        track: Optional track name to filter by
        start_time: Optional start time in beats (inclusive)
        end_time: Optional end time in beats (exclusive)

    Returns:
        List of note dictionaries matching the filters

    Examples:
        >>> get_notes()  # Get all notes
        >>> get_notes(track="piano")  # Get all piano notes
        >>> get_notes(track="piano", start_time=0, end_time=4)  # Piano notes in beats 0-4
    """
    state = get_state()
    notes = state.notes

    # Filter by track if specified
    if track is not None:
        notes = [n for n in notes if n.get("track") == track]

    # Filter by time range if specified
    if start_time is not None or end_time is not None:
        filtered = []
        for n in notes:
            note_start = _eval_expression(n.get("start", 0))

            # Apply start_time filter
            if start_time is not None and note_start < start_time:
                continue

            # Apply end_time filter
            if end_time is not None and note_start >= end_time:
                continue

            filtered.append(n)

        notes = filtered

    # Return a copy to prevent external modification
    return [n.copy() for n in notes]
