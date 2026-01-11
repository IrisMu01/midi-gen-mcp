"""Utility tools (undo, redo, export)."""

from midi_gen_mcp.state import undo_last_action, redo_last_action
from midi_gen_mcp.midi_export import export_midi as _export_midi


def undo() -> str:
    """
    Undo the last action.

    Returns:
        Confirmation message or error if nothing to undo
    """
    return undo_last_action()


def redo() -> str:
    """
    Redo the last undone action.

    Returns:
        Confirmation message or error if nothing to redo
    """
    return redo_last_action()


def export_midi(filepath: str) -> str:
    """
    Export the current piece to a MIDI file.

    Args:
        filepath: Path to save the MIDI file (should end in .mid or .midi)

    Returns:
        Confirmation message with file info
    """
    return _export_midi(filepath)
