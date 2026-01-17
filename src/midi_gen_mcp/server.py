"""MCP Server for MIDI Generation.

This module implements the main MCP server with all MIDI generation tools.
The server exposes low-level CRUD operations for MIDI composition, keeping
all creative reasoning in the LLM (Claude).
"""

import asyncio
from typing import Any, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field

# Import all tool functions
from midi_gen_mcp.tools.song import set_title, get_piece_info
from midi_gen_mcp.tools.structure import add_section, edit_section, get_sections
from midi_gen_mcp.tools.track import add_track, remove_track, get_tracks
from midi_gen_mcp.tools.note import add_notes, remove_notes_in_range, get_notes
from midi_gen_mcp.tools.harmony import add_chords, get_chords_in_range, remove_chords_in_range
from midi_gen_mcp.tools.validation import flag_notes, remove_flagged_notes
from midi_gen_mcp.tools.utility import undo, redo, export_midi


# Initialize MCP server
app = Server("midi-gen-mcp")


# ============================================================================
# Pydantic Models for Tool Parameters
# ============================================================================

class SetTitleParams(BaseModel):
    """Parameters for set_title."""
    title: str = Field(..., description="The title for the piece")


class AddSectionParams(BaseModel):
    """Parameters for add_section."""
    name: str = Field(..., description="Section name (must be unique)")
    start_measure: int = Field(..., description="Starting measure (1-indexed)", ge=1)
    end_measure: int = Field(..., description="Ending measure (inclusive)", ge=1)
    tempo: int = Field(..., description="Tempo in BPM", ge=1, le=300)
    time_signature: str = Field(..., description="Time signature (e.g., '4/4', '6/8')")
    key: str = Field(..., description="Key signature (e.g., 'C', 'Am', 'F#m')")
    description: str = Field(default="", description="Optional description/journal")


class EditSectionParams(BaseModel):
    """Parameters for edit_section."""
    name: str = Field(..., description="Name of the section to edit")
    start_measure: Optional[int] = Field(None, description="New starting measure", ge=1)
    end_measure: Optional[int] = Field(None, description="New ending measure", ge=1)
    tempo: Optional[int] = Field(None, description="New tempo in BPM", ge=1, le=300)
    time_signature: Optional[str] = Field(None, description="New time signature")
    key: Optional[str] = Field(None, description="New key signature")
    description: Optional[str] = Field(None, description="New description")


class AddTrackParams(BaseModel):
    """Parameters for add_track."""
    name: str = Field(..., description="Track name (must be unique)")
    instrument: str = Field(..., description="Instrument name (e.g., 'piano', 'violin', 'drums')")


class RemoveTrackParams(BaseModel):
    """Parameters for remove_track."""
    name: str = Field(..., description="Name of the track to remove")


class NoteDict(BaseModel):
    """A single note."""
    track: str = Field(..., description="Track name (must exist)")
    pitch: int = Field(..., description="MIDI note number (0-127)", ge=0, le=127)
    start: Any = Field(..., description="Start time in beats (quarter notes), can be number or expression like '9 + 1/3'")
    duration: Any = Field(..., description="Duration in beats, can be number or expression like '1/3'")


class AddNotesParams(BaseModel):
    """Parameters for add_notes."""
    notes: list[NoteDict] = Field(..., description="List of notes to add")


class RemoveNotesInRangeParams(BaseModel):
    """Parameters for remove_notes_in_range."""
    track: str = Field(..., description="Track name")
    start_time: float = Field(..., description="Start time in beats (inclusive)")
    end_time: float = Field(..., description="End time in beats (exclusive)")


class GetNotesParams(BaseModel):
    """Parameters for get_notes."""
    track: Optional[str] = Field(None, description="Optional track name to filter by")
    start_time: Optional[float] = Field(None, description="Optional start time in beats (inclusive)")
    end_time: Optional[float] = Field(None, description="Optional end time in beats (exclusive)")


class ExportMidiParams(BaseModel):
    """Parameters for export_midi."""
    filepath: str = Field(..., description="Path to save the MIDI file (should end in .mid or .midi)")


class ChordDict(BaseModel):
    """A single chord entry."""
    beat: float = Field(..., description="Beat position where chord starts")
    chord: str = Field(..., description="Chord symbol (e.g., 'C', 'Cm7', 'G7', 'Fmaj9')")
    duration: float = Field(..., description="Duration of the chord in beats")


class AddChordsParams(BaseModel):
    """Parameters for add_chords."""
    chords: list[ChordDict] = Field(..., description="List of chords to add")


class GetChordsInRangeParams(BaseModel):
    """Parameters for get_chords_in_range."""
    start_beat: float = Field(..., description="Start of the beat range")
    end_beat: float = Field(..., description="End of the beat range")


class RemoveChordsInRangeParams(BaseModel):
    """Parameters for remove_chords_in_range."""
    start_beat: float = Field(..., description="Start of the beat range")
    end_beat: float = Field(..., description="End of the beat range")


class FlagNotesParams(BaseModel):
    """Parameters for flag_notes."""
    tracks: list[str] = Field(..., description="List of track names to check")
    start_beat: float = Field(..., description="Start of the beat range")
    end_beat: float = Field(..., description="End of the beat range")


# ============================================================================
# Tool Registration
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MIDI generation tools."""
    return [
        # Song Management
        Tool(
            name="set_title",
            description="Set the title of the musical piece",
            inputSchema=SetTitleParams.model_json_schema()
        ),
        Tool(
            name="get_piece_info",
            description="Get overview information about the current piece (title, sections, tracks, note count)",
            inputSchema={"type": "object", "additionalProperties": "false"}
        ),

        # Structure Management
        Tool(
            name="add_section",
            description="Add a new section to the piece with tempo, time signature, and key",
            inputSchema=AddSectionParams.model_json_schema()
        ),
        Tool(
            name="edit_section",
            description="Edit an existing section (automatically adjusts neighbors to prevent overlaps)",
            inputSchema=EditSectionParams.model_json_schema()
        ),
        Tool(
            name="get_sections",
            description="Get all sections in the piece",
            inputSchema={"type": "object", "additionalProperties": "false"}
        ),

        # Track Management
        Tool(
            name="add_track",
            description="Add a new track to the piece",
            inputSchema=AddTrackParams.model_json_schema()
        ),
        Tool(
            name="remove_track",
            description="Remove a track and all its notes",
            inputSchema=RemoveTrackParams.model_json_schema()
        ),
        Tool(
            name="get_tracks",
            description="Get all tracks in the piece",
            inputSchema={"type": "object", "additionalProperties": "false"}
        ),

        # Note Operations
        Tool(
            name="add_notes",
            description="Add multiple notes to the piece (batch operation). Supports expression syntax for timing (e.g., '9 + 1/3')",
            inputSchema=AddNotesParams.model_json_schema()
        ),
        Tool(
            name="remove_notes_in_range",
            description="Remove all notes in a track within a time range",
            inputSchema=RemoveNotesInRangeParams.model_json_schema()
        ),
        Tool(
            name="get_notes",
            description="Query notes, optionally filtered by track and/or time range",
            inputSchema=GetNotesParams.model_json_schema()
        ),

        # Harmony Tools
        Tool(
            name="add_chords",
            description="Add chord progression to the piece. Validates chord symbols and returns chord tones for each chord.",
            inputSchema=AddChordsParams.model_json_schema()
        ),
        Tool(
            name="get_chords_in_range",
            description="Get all chords in a beat range",
            inputSchema=GetChordsInRangeParams.model_json_schema()
        ),
        Tool(
            name="remove_chords_in_range",
            description="Remove chords in a beat range. Also clears all flagged notes since harmony context becomes stale.",
            inputSchema=RemoveChordsInRangeParams.model_json_schema()
        ),

        # Validation Tools
        Tool(
            name="flag_notes",
            description="Flag notes that fall outside the planned chord progression. Useful for detecting melody-harmony conflicts.",
            inputSchema=FlagNotesParams.model_json_schema()
        ),
        Tool(
            name="remove_flagged_notes",
            description="Remove all flagged notes from the piece",
            inputSchema={"type": "object", "additionalProperties": "false"}
        ),

        # Utility
        Tool(
            name="undo",
            description="Undo the last action (max 10 undo steps)",
            inputSchema={"type": "object", "additionalProperties": "false"}
        ),
        Tool(
            name="redo",
            description="Redo the last undone action",
            inputSchema={"type": "object", "additionalProperties": "false"}
        ),
        Tool(
            name="export_midi",
            description="Export the current piece to a MIDI file",
            inputSchema=ExportMidiParams.model_json_schema()
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution."""
    try:
        result = None

        # Song Management
        if name == "set_title":
            params = SetTitleParams(**arguments)
            result = set_title(params.title)

        elif name == "get_piece_info":
            result = get_piece_info()

        # Structure Management
        elif name == "add_section":
            params = AddSectionParams(**arguments)
            result = add_section(
                name=params.name,
                start_measure=params.start_measure,
                end_measure=params.end_measure,
                tempo=params.tempo,
                time_signature=params.time_signature,
                key=params.key,
                description=params.description
            )

        elif name == "edit_section":
            params = EditSectionParams(**arguments)
            kwargs = {}
            if params.start_measure is not None:
                kwargs["start_measure"] = params.start_measure
            if params.end_measure is not None:
                kwargs["end_measure"] = params.end_measure
            if params.tempo is not None:
                kwargs["tempo"] = params.tempo
            if params.time_signature is not None:
                kwargs["time_signature"] = params.time_signature
            if params.key is not None:
                kwargs["key"] = params.key
            if params.description is not None:
                kwargs["description"] = params.description
            result = edit_section(params.name, **kwargs)

        elif name == "get_sections":
            result = get_sections()

        # Track Management
        elif name == "add_track":
            params = AddTrackParams(**arguments)
            result = add_track(params.name, params.instrument)

        elif name == "remove_track":
            params = RemoveTrackParams(**arguments)
            result = remove_track(params.name)

        elif name == "get_tracks":
            result = get_tracks()

        # Note Operations
        elif name == "add_notes":
            params = AddNotesParams(**arguments)
            # Convert Pydantic models to dicts
            notes_list = [note.model_dump() for note in params.notes]
            result = add_notes(notes_list)

        elif name == "remove_notes_in_range":
            params = RemoveNotesInRangeParams(**arguments)
            result = remove_notes_in_range(params.track, params.start_time, params.end_time)

        elif name == "get_notes":
            params = GetNotesParams(**arguments)
            result = get_notes(
                track=params.track,
                start_time=params.start_time,
                end_time=params.end_time
            )

        # Harmony Tools
        elif name == "add_chords":
            params = AddChordsParams(**arguments)
            # Convert Pydantic models to dicts
            chords_list = [chord.model_dump() for chord in params.chords]
            result = add_chords(chords_list)

        elif name == "get_chords_in_range":
            params = GetChordsInRangeParams(**arguments)
            result = get_chords_in_range(params.start_beat, params.end_beat)

        elif name == "remove_chords_in_range":
            params = RemoveChordsInRangeParams(**arguments)
            result = remove_chords_in_range(params.start_beat, params.end_beat)

        # Validation Tools
        elif name == "flag_notes":
            params = FlagNotesParams(**arguments)
            result = flag_notes(params.tracks, params.start_beat, params.end_beat)

        elif name == "remove_flagged_notes":
            result = remove_flagged_notes()

        # Utility
        elif name == "undo":
            result = undo()

        elif name == "redo":
            result = redo()

        elif name == "export_midi":
            params = ExportMidiParams(**arguments)
            result = export_midi(params.filepath)

        else:
            raise ValueError(f"Unknown tool: {name}")

        # Format result as TextContent
        if isinstance(result, str):
            content = result
        elif isinstance(result, (dict, list)):
            import json
            content = json.dumps(result, indent=2)
        else:
            content = str(result)

        return [TextContent(type="text", text=content)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def run():
    """Entry point for the server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
