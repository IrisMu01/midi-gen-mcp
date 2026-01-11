"""Track management tools."""

from midi_gen_mcp.state import get_state, before_mutation


def add_track(name: str, instrument: str) -> str:
    """
    Add a new track to the piece.

    Args:
        name: Track name (must be unique)
        instrument: Instrument name (e.g., "piano", "violin", "drums")

    Returns:
        Confirmation message
    """
    before_mutation()
    state = get_state()

    # Check for duplicate name
    if name in state.tracks:
        return f"Error: Track '{name}' already exists"

    state.tracks[name] = {
        "name": name,
        "instrument": instrument
    }

    return f"Added track '{name}' ({instrument})"


def remove_track(name: str) -> str:
    """
    Remove a track and all its notes.

    Args:
        name: Name of the track to remove

    Returns:
        Confirmation message
    """
    before_mutation()
    state = get_state()

    if name not in state.tracks:
        return f"Error: Track '{name}' not found"

    # Remove the track
    del state.tracks[name]

    # Remove all notes associated with this track
    notes_removed = 0
    state.notes = [n for n in state.notes if n.get("track") != name]
    notes_removed = len([n for n in state.notes if n.get("track") == name])

    return f"Removed track '{name}' (and {notes_removed} notes)"


def get_tracks() -> dict[str, dict]:
    """
    Get all tracks in the piece.

    Returns:
        Dictionary mapping track names to track info
    """
    state = get_state()
    return state.tracks.copy()
