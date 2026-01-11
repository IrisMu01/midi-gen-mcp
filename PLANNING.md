# MCP Server Planning Summary

## Context

This repo implements **Core Component #1: MCP Server** from `design_doc.md`. The MCP server exposes low-level CRUD operations for MIDI generation, keeping all creative reasoning in the LLM (Claude Sonnet 4.5).

**Key Principle**: MCP tools are deterministic operations only. All music theory and composition happens in Claude through skills.

---

## MCP Server Structure

```
midi-gen-mcp/
├── src/
│   └── midi_gen_mcp/
│       ├── __init__.py
│       ├── server.py          # Main MCP server entry point
│       ├── state.py           # In-memory state management
│       ├── tools/             # Tool implementations (one file per category)
│       │   ├── __init__.py
│       │   ├── song.py        # create_song, get_song_info
│       │   ├── structure.py   # add_section, edit_section, get_sections
│       │   ├── track.py       # add_track, remove_track, get_tracks
│       │   ├── note.py        # add_notes, remove_notes_in_range, get_notes
│       │   └── utility.py     # undo_last_action, redo_last_action, export_midi
│       └── midi_export.py     # MIDI file generation (using mido)
├── tests/
│   └── test_*.py
├── pyproject.toml
├── README.md
├── design_doc.md
└── PLANNING.md (this file)
```

---

## State Schema (Normalized)

```python
@dataclass
class State:
    title: str       # Piece title (default: "Untitled")
    tracks: dict     # {track_name: {name: str, instrument: str}}
    notes: list      # [{track: str, pitch: int, start: str/float, duration: str/float}]
    sections: list   # [{name, start_measure, end_measure, tempo, time_signature, key, description}]
    undo_stack: list # Max 10 state snapshots
    redo_stack: list # Cleared on new action
```

### Key Design Decisions:

1. **No global song_info**: Removed in favor of `title` field + per-section tempo/time_signature/key
2. **Tempo/time_signature/key per section**: Allows for tempo changes, meter changes, and modulation
3. **Normalized structure**: Notes in flat list, not nested under tracks (optimized for range queries)
4. **No separate journal**: `sections[].description` serves both planning and execution notes
5. **Expression support**: Note `start`/`duration` can be strings like `"9 + 1/3"` (evaluated to beats)
6. **Beat-based timing**: Always in quarter notes (MIDI standard), time-signature agnostic
7. **Neighbor adjustment**: Editing section boundaries automatically trims neighboring sections to prevent overlaps

### Example Note:
```python
{
  "track": "piano",
  "pitch": 60,           # Middle C
  "start": "9 + 1/3",    # Beats (quarter notes) - supports expressions
  "duration": "1/3"      # Triplet eighth note
}
```

### Example Section:
```python
{
  "name": "intro",
  "start_measure": 1,
  "end_measure": 4,
  "tempo": 72,
  "time_signature": "4/4",
  "key": "Dm",
  "description": "Sparse piano, melancholic. Dm9-G7alt progression, descending melody..."
}
```

---

## Libraries & Dependencies

| Library | Purpose | Usage |
|---------|---------|-------|
| **`mcp`** | MCP server framework | Tool registration, stdio transport, schema generation |
| **`mido`** | MIDI file I/O | Export to `.mid` files (note_on/note_off events) |
| **`pydantic`** | Data validation | Tool parameter validation (included with `mcp`) |
| **`json`** (stdlib) | State persistence | Optional save/load session |
| **`copy`** (stdlib) | Deep copying | Undo/redo state snapshots |
| **`dataclasses`** (stdlib) | Data structures | Internal state objects |

---

## Key Algorithms

### 1. Undo/Redo (State Snapshots)

**Memory limit**: Max 10 undo actions

```python
def before_mutation():
    """Call before ANY mutating operation"""
    state.undo_stack.append(snapshot_state())

    # Limit to 10 snapshots
    if len(state.undo_stack) > 10:
        state.undo_stack.pop(0)  # Remove oldest

    state.redo_stack.clear()  # New action invalidates redo

def undo_last_action():
    if not state.undo_stack:
        return "Nothing to undo"

    state.redo_stack.append(snapshot_state())
    previous = state.undo_stack.pop()
    restore_state(previous)
    return "Undone"

def redo_last_action():
    if not state.redo_stack:
        return "Nothing to redo"

    state.undo_stack.append(snapshot_state())
    next_state = state.redo_stack.pop()
    restore_state(next_state)
    return "Redone"
```

**Memory cost**: ~400KB/snapshot × 10 = ~4MB (acceptable)

---

### 2. MIDI Export

**Process**:
1. Evaluate expressions (`"9 + 1/3"` → `9.333...`) and convert to absolute ticks
2. Create note_on/note_off events with absolute tick times
3. Sort events by tick (note_off after note_on if same tick)
4. Convert to delta times (relative to previous event)
5. Write MIDI file with one track per instrument

**Key constants**:
- `TICKS_PER_BEAT = 480` (standard resolution)
- Fixed velocity = 64 (medium, no dynamics for prototype)
- One MIDI track per instrument (channels 0-15)

**MIDI message structure**:
```python
Message('note_on',
        note=60,        # MIDI note number (0-127)
        velocity=64,    # How hard struck (0-127)
        channel=0,      # Instrument channel (0-15)
        time=160)       # Delta time in ticks since last event
```

**Example conversion**:
```python
# Input note
{"pitch": 60, "start": "9 + 1/3", "duration": "1/3"}

# Step 1: Evaluate and convert to ticks
start_beats = 9.333...
start_ticks = int(9.333... × 480) = 4480 ticks
duration_ticks = int(0.333... × 480) = 160 ticks
end_ticks = 4480 + 160 = 4640 ticks

# Step 2: Create events
events = [
  {'type': 'note_on', 'note': 60, 'tick': 4480},
  {'type': 'note_off', 'note': 60, 'tick': 4640}
]

# Step 3: Sort and compute deltas (if prev event at tick 4000)
Message('note_on', note=60, time=480)   # delta = 4480 - 4000
Message('note_off', note=60, time=160)  # delta = 4640 - 4480
```

---

## MCP Tools Overview

### Song Management
- `set_title(title: str)` - Set piece title
- `get_piece_info()` - Return title, sections overview, tracks, note count

### Structure Management
- `add_section(name, start_measure, end_measure, tempo, time_signature, key, description)` - Add section
- `edit_section(name: str, **kwargs)` - Update section fields (auto-adjusts neighbors to prevent overlaps)
- `get_sections()` - Return all sections

### Track Management
- `add_track(name: str, instrument: str)` - Create track
- `remove_track(name: str)` - Delete track and its notes
- `get_tracks()` - Return all tracks

### Note Operations (Core CRUD)
- `add_notes(notes: List[dict])` - Batch add notes
- `remove_notes_in_range(track: str, start_time: float, end_time: float)` - Delete notes in time range
- `get_notes(track: str, start_time: float, end_time: float)` - Query notes (supports expressions)

### Utility
- `undo_last_action()` - Restore previous state
- `redo_last_action()` - Restore undone state
- `export_midi(filepath: str)` - Generate `.mid` file

---

## Execution Plan

### Task 1: Project Scaffolding ✅
- [x] Set up Python project structure (pyproject.toml, src/, tests/)
- [x] Install dependencies: `mcp`, `mido`, `pytest`
- [x] Initialize git workflow on branch `claude/plan-mcp-server-cqlSM`
- [x] Add requirements.txt and Makefile for easy setup

### Task 2: Core State & Server
- [x] Implement `state.py` with State dataclass and snapshot functions
- [x] Implement undo/redo with 10-snapshot limit
- [ ] Implement `server.py` with MCP server initialization (stdio transport)
- [ ] Add basic tool registration skeleton

### Task 3: Song & Structure Tools ✅
- [x] Implement `tools/song.py` (set_title, get_piece_info)
- [x] Implement `tools/structure.py` (add_section, edit_section, get_sections)
- [x] Implement neighbor adjustment logic for section overlaps
- [x] Write comprehensive unit tests (18 tests)
- [ ] Wire to server and test

### Task 4: Track & Note Tools
- [x] Implement `tools/track.py` (add_track, remove_track, get_tracks)
- [x] Write unit tests for track operations (9 tests)
- [ ] Implement `tools/note.py` (add_notes, remove_notes_in_range, get_notes)
- [ ] Support expression evaluation for note timing

### Task 5: MIDI Export
- [ ] Implement `midi_export.py` with expression eval and tick conversion
- [ ] Handle note_on/note_off event generation and sorting
- [ ] Support multi-track export with channels
- [ ] Add General MIDI instrument mapping

### Task 6: Utility Tools
- [x] Implement undo/redo in `state.py` (enforces 10-snapshot limit)
- [ ] Implement `tools/utility.py` wrapper (undo, redo, export)
- [ ] Wire export to midi_export module

### Task 7: Testing & Validation
- [x] Unit tests for state operations (8 tests)
- [x] Unit tests for song, structure, track tools (27 tests total)
- [ ] Integration test: Create simple song via MCP tools
- [ ] Export test MIDI and validate in external DAW
- [x] Test undo/redo stack behavior

### Task 8: Documentation & Commit
- [ ] Update README with setup instructions
- [ ] Document tool schemas
- [x] Commit and push regularly to `claude/plan-mcp-server-cqlSM`

**Current Status**: 35/35 tests passing. State management, song, structure, and track tools complete.

---

## Success Criteria

- [ ] MCP server runs via Claude Desktop
- [x] All implemented tools execute without errors (song, structure, track)
- [ ] Expression evaluation works (`"9 + 1/3"` → correct ticks)
- [ ] MIDI export produces valid `.mid` files
- [x] Undo/redo limited to 10 actions, no memory leaks
- [ ] Can compose 8-bar melody with multiple tracks
- [ ] Exported MIDI sounds correct in external DAW (MuseScore, Logic, etc.)

**Achieved so far**: State management, undo/redo, song/structure/track tools with 35 passing unit tests.

---

## Next Steps

Once MCP server is complete and validated:
1. **Phase 2**: Create music theory skills (harmony, melody, rhythm, genres)
2. **Phase 3**: Build minimal frontend (Electron + React chat interface)
3. **Phase 4**: Add piano roll visualization and manual editing

Current focus: **MCP server only** (this repo scope)
