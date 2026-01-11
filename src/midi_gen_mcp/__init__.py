"""MCP server for AI-integrated DAW with low-level MIDI operations."""

__version__ = "0.1.0"

from midi_gen_mcp.server import app, run

__all__ = ["app", "run", "__version__"]
