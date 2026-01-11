"""MCP tools for MIDI manipulation."""

from midi_gen_mcp.tools.song import set_title, get_piece_info
from midi_gen_mcp.tools.structure import add_section, edit_section, get_sections
from midi_gen_mcp.tools.track import add_track, remove_track, get_tracks
from midi_gen_mcp.tools.note import add_notes, remove_notes_in_range, get_notes
from midi_gen_mcp.tools.utility import undo, redo, export_midi

__all__ = [
    # Song management
    "set_title",
    "get_piece_info",
    # Structure management
    "add_section",
    "edit_section",
    "get_sections",
    # Track management
    "add_track",
    "remove_track",
    "get_tracks",
    # Note operations
    "add_notes",
    "remove_notes_in_range",
    "get_notes",
    # Utility
    "undo",
    "redo",
    "export_midi",
]
