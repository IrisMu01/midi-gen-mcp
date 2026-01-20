"""Track management tools."""

from midi_gen_mcp.state import get_state, before_mutation


def add_track(name: str, instrument: str, volume: int = 100, pan: int = 64) -> str:
    """
    Add a new track to the piece.

    Args:
        name: Track name (must be unique)
        instrument: Instrument name (e.g., "piano", "violin", "drums")
        volume: Track volume (0-127, default 100) - MIDI CC7
        pan: Track pan (0=hard left, 64=center, 127=hard right, default 64) - MIDI CC10

    Returns:
        Confirmation message
    """
    before_mutation()
    state = get_state()

    # Check for duplicate name
    if name in state.tracks:
        return f"Error: Track '{name}' already exists"

    # Validate volume range
    if not (0 <= volume <= 127):
        return f"Error: volume must be 0-127, got {volume}"

    # Validate pan range
    if not (0 <= pan <= 127):
        return f"Error: pan must be 0-127, got {pan}"

    state.tracks[name] = {
        "name": name,
        "instrument": instrument,
        "volume": volume,
        "pan": pan
    }

    return f"Added track '{name}' ({instrument})"


def edit_track(name: str, volume: int = None, pan: int = None) -> str:
    """
    Edit an existing track's volume and/or pan settings.

    Args:
        name: Name of the track to edit (must exist)
        volume: New volume (0-127, optional) - MIDI CC7
        pan: New pan (0-127, optional) - MIDI CC10

    Returns:
        Confirmation message

    Note:
        This function only updates the track settings, not the notes.
        At least one of volume or pan must be provided.
    """
    before_mutation()
    state = get_state()

    # Check track exists
    if name not in state.tracks:
        return f"Error: Track '{name}' not found"

    # Check that at least one parameter is provided
    if volume is None and pan is None:
        return "Error: Must specify at least one of volume or pan to edit"

    # Validate volume if provided
    if volume is not None:
        if not isinstance(volume, int) or not (0 <= volume <= 127):
            return f"Error: volume must be 0-127, got {volume}"

    # Validate pan if provided
    if pan is not None:
        if not isinstance(pan, int) or not (0 <= pan <= 127):
            return f"Error: pan must be 0-127, got {pan}"

    # Update track settings
    track = state.tracks[name]
    updated = []

    if volume is not None:
        track["volume"] = volume
        updated.append(f"volume={volume}")

    if pan is not None:
        track["pan"] = pan
        updated.append(f"pan={pan}")

    return f"Updated track '{name}' ({', '.join(updated)})"


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
