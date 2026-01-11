"""Song/piece management tools."""

from midi_gen_mcp.state import get_state, before_mutation


def set_title(title: str) -> str:
    """
    Set the title of the musical piece.

    Args:
        title: The title for the piece

    Returns:
        Confirmation message
    """
    before_mutation()
    state = get_state()
    state.title = title
    return f"Title set to: {title}"


def get_piece_info() -> dict:
    """
    Get overview information about the current piece.

    Returns:
        Dictionary with title, number of sections, tracks, and notes
    """
    state = get_state()
    return {
        "title": state.title,
        "num_sections": len(state.sections),
        "num_tracks": len(state.tracks),
        "num_notes": len(state.notes),
        "sections": [
            {
                "name": s["name"],
                "measures": f"{s['start_measure']}-{s['end_measure']}",
                "tempo": s.get("tempo"),
                "time_signature": s.get("time_signature"),
                "key": s.get("key")
            }
            for s in state.sections
        ],
        "tracks": list(state.tracks.keys())
    }
