# CLAUDE.md - Codebase Overview

Quick reference for understanding the MIDI Gen MCP server architecture.

---

## Architecture Overview

This is an **MCP (Model Context Protocol) server** that provides MIDI composition tools to LLMs like Claude. The LLM handles all creative reasoning; the server provides low-level CRUD operations.

**Design Philosophy:**
- Server = stateful CRUD operations only
- LLM = all creative decisions and musical reasoning
- Undo/redo support for all mutations
- Expression syntax for precise timing (e.g., `"9 + 1/3"` beats)

---

## Directory Structure

```
src/midi_gen_mcp/
├── server.py              # MCP server entry point, tool registration
├── state.py               # Global state management + undo/redo
├── midi_export.py         # MIDI file generation
├── chord_parser.py        # Chord symbol parsing (C, Cm7, Gmaj9, etc.)
└── tools/                 # Tool implementations
    ├── song.py            # Title, piece info
    ├── structure.py       # Sections (measures, tempo, time signature)
    ├── track.py           # Tracks (instrument, volume, pan)
    ├── note.py            # Note operations (add, remove, query)
    ├── harmony.py         # Chord progression tracking
    ├── validation.py      # Melody-harmony conflict detection
    └── utility.py         # Undo, redo, export

tests/                     # 137 pytest tests (100% passing)
```

---

## Core Modules

### 📡 **server.py** - MCP Server Interface
- **Purpose:** Exposes tools to LLMs via Model Context Protocol
- **Key Components:**
  - Pydantic schemas for tool parameters (validation + type safety)
  - Tool registration via `@app.list_tools()`
  - Tool execution via `@app.call_tool()`
- **Important:** This is the **only** interface LLMs use. If a feature isn't in a Pydantic schema here, the LLM can't use it.

### 🗄️ **state.py** - State Management
- **Purpose:** In-memory state for a single musical piece
- **State Fields:**
  - `title`: Song title
  - `tracks`: Dict of `{track_name: {instrument, volume, pan}}`
  - `notes`: List of `{track, pitch, start, duration, velocity?}`
  - `sections`: List of `{name, start_measure, end_measure, tempo, time_signature, key}`
  - `chord_progression`: List of `{beat, chord, duration, chord_tones}`
  - `undo_stack`, `redo_stack`: Snapshots for undo/redo (max 10)
- **Key Functions:**
  - `before_mutation()`: Call before ANY state change to enable undo
  - `snapshot_state()`: Deep copy of current state (excludes undo/redo stacks)
  - `restore_state()`: Restore from snapshot

### 🎵 **midi_export.py** - MIDI File Generation
- **Purpose:** Convert in-memory state to .mid files
- **Key Features:**
  - **Tempo Track (Track 0):** All tempo changes across sections
  - **Instrument Tracks:** One track per instrument with program_change, CC7 (volume), CC10 (pan)
  - **Note velocity:** Per-note dynamics (0-127)
  - **Expression evaluation:** Converts timing expressions to ticks
- **Functions:**
  - `export_midi(filepath)`: Main export function
  - `_calculate_section_beat_offset()`: Handles varying time signatures
  - `_get_instrument_program()`: Maps instrument names → GM program numbers

### 🎸 **chord_parser.py** - Chord Symbol Parser
- **Purpose:** Parse chord symbols into MIDI note numbers
- **Supported:** Major, minor, 7th, maj7, m7, dim, aug, sus4, 9th, add9, 6, etc.
- **Returns:** List of MIDI note numbers (chord tones) for each chord

---

## Tool Modules (`tools/`)

### **song.py** - Song Metadata
- `set_title(title)`: Set piece title
- `get_piece_info()`: Overview (title, sections, tracks, note count)

### **structure.py** - Section Management
- `add_section(name, start_measure, end_measure, tempo, time_signature, key, description)`
  - Defines musical structure (verse, chorus, bridge, etc.)
  - Auto-sorts sections by `start_measure`
- `edit_section(name, **kwargs)`: Update section properties
  - Auto-adjusts neighbors to prevent overlaps
- `get_sections()`: Query all sections

### **track.py** - Track Management
- `add_track(name, instrument, volume=100, pan=64)`:
  - Instrument: GM instrument name (e.g., `"piano"`, `"violin"`)
  - Volume: MIDI CC7 (0-127, default 100)
  - Pan: MIDI CC10 (0=left, 64=center, 127=right)
- `edit_track(name, volume?, pan?)`: Update track volume/pan without affecting notes
  - At least one of volume or pan must be provided
  - Does not modify existing notes
- `remove_track(name)`: Remove track + all notes
- `get_tracks()`: Query all tracks

### **note.py** - Note Operations
- `add_notes(notes)`: Batch add notes
  - Schema: `{track, pitch, start, duration, velocity?}`
  - `start`/`duration`: Numbers or expressions (e.g., `"9 + 1/3"`)
  - `velocity`: Optional (0-127, default 64 during export)
- `remove_notes_in_range(track, start_time, end_time)`: Remove notes in time range
- `get_notes(track?, start_time?, end_time?)`: Query notes with filters

### **harmony.py** - Chord Progression
- `add_chords(chords)`: Add chord progression
  - Schema: `{beat, chord, duration}`
  - Validates chord symbols via `chord_parser.py`
  - Returns chord tones for each chord
  - Handles overlaps (splits/replaces earlier chords)
- `get_chords_in_range(start_beat, end_beat)`: Query chords
- `remove_chords_in_range(start_beat, end_beat)`: Remove chords

### **validation.py** - Melody-Harmony Validation
- `flag_notes(tracks, start_beat, end_beat)`:
  - Flags notes outside chord progression (melody-harmony conflicts)
  - Uses `chord_tones` from chord_progression
  - Sets `"flagged": true` on conflicting notes
- `remove_flagged_notes()`: Remove all flagged notes

### **utility.py** - Undo/Redo/Export
- `undo()`: Undo last action (max 10 steps)
- `redo()`: Redo last undone action
- `export_midi(filepath)`: Export to .mid file

---

## Key Concepts

### 🔄 **Undo/Redo System**
- **Trigger:** Call `before_mutation()` before ANY state change
- **Mechanism:** Deep copy of state pushed to `undo_stack`
- **Limitation:** Max 10 snapshots (memory management)
- **Invalidation:** New action clears `redo_stack`

### 📐 **Time Representation**
- **Beats:** Quarter notes (480 MIDI ticks per beat)
- **Measures:** Defined by sections with `time_signature`
- **Expressions:** String expressions like `"9 + 1/3"` evaluated via `eval()` (sandboxed)

### 🎹 **MIDI Mapping**
- **Channels:** 0-15 (channel 9 reserved for drums)
- **Programs:** GM instrument numbers (0-127)
- **Velocity:** 0-127 (note dynamics)
- **CC7:** Volume (0-127)
- **CC10:** Pan (0=left, 64=center, 127=right)

### 🏗️ **Section-Based Structure**
Sections define musical structure with independent tempo/time signature:
```python
{
  "name": "verse",
  "start_measure": 5,
  "end_measure": 12,
  "tempo": 120,           # BPM
  "time_signature": "4/4",
  "key": "C",
  "description": "..."
}
```

Tempo changes export to dedicated **Tempo Track (Track 0)** in MIDI files.

---

## Testing

- **Location:** `tests/` directory
- **Framework:** pytest
- **Coverage:** 137 tests (100% passing)
- **Categories:**
  - Unit tests for each tool module
  - MIDI export validation
  - Undo/redo compatibility
  - Invalid input handling
  - Boundary value testing

**Run tests:**
```bash
python -m pytest tests/ -v
```

---

## Development Workflow

### Adding a New Feature

1. **Update backend logic** (`tools/` or core modules)
2. **Update Pydantic schema** in `server.py` (critical!)
3. **Update call_tool handler** in `server.py`
4. **Add tests** in `tests/`
5. **Update PLANNING.md** if needed

### Debugging Tips

- All tools return strings or JSON-serializable dicts/lists
- Error messages prefixed with `"Error: "`
- State is global - use `reset_state()` in tests
- MIDI export uses Track 0 for tempo (instrument tracks start at 1)

---

## File Reference Quick Index

| File | Purpose |
|------|---------|
| `server.py` | MCP tool registration + LLM interface |
| `state.py` | Global state + undo/redo |
| `midi_export.py` | MIDI file generation |
| `chord_parser.py` | Chord symbol → MIDI notes |
| `tools/song.py` | Title, piece info |
| `tools/structure.py` | Sections (measures, tempo, time sig) |
| `tools/track.py` | Tracks (instrument, volume, pan) |
| `tools/note.py` | Note CRUD operations |
| `tools/harmony.py` | Chord progression tracking |
| `tools/validation.py` | Melody-harmony conflict detection |
| `tools/utility.py` | Undo, redo, export |

---

## Recent Changes (January 2025)

### MIDI Quality Improvements
- ✅ **Multiple tempo changes:** Dedicated Tempo Track (Track 0) supports tempo changes across sections
- ✅ **Note velocity:** Optional `velocity` field (0-127, default 64) for dynamics
- ✅ **Track volume/pan:** CC7 (volume) and CC10 (pan) support in `add_track()`

All changes are backwards compatible with optional parameters.
