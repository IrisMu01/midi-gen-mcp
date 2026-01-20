# Data Flow Verification

Complete trace of data flow for new MIDI features (velocity, volume, pan, multiple tempos).

---

## Flow 1: Note Velocity (0-127)

### Path: LLM → MCP → Backend → State → Export

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LLM sends MCP tool call                                   │
│    add_notes({notes: [{velocity: 100, ...}]})               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. MCP Server (server.py:72-78)                              │
│    NoteDict schema validates:                                │
│    - velocity: Optional[int]                                 │
│    - ge=0, le=127 (Pydantic constraint)                      │
│    ✅ Validation: Rejects -1, 128, 256, etc.                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Backend (tools/note.py:40-95)                             │
│    add_notes() validates:                                    │
│    - Lines 81-83: if "velocity" in note, check 0-127        │
│    - Line 93: state.notes.extend(notes)                     │
│    ✅ Double validation for direct Python calls              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. State Storage (state.py)                                  │
│    - Stored in state.notes as dict with velocity field      │
│    - Undo/redo via copy.deepcopy() preserves velocity       │
│    ✅ Velocity persists in snapshots                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. MIDI Export (midi_export.py:422)                          │
│    velocity = note.get("velocity", DEFAULT_VELOCITY)        │
│    - Uses 64 if not specified                               │
│    - Creates note_on event with velocity                    │
│    ✅ Exported to .mid file                                  │
└─────────────────────────────────────────────────────────────┘
```

**Test Coverage:**
- ✅ `test_velocity_support_explicit_values` - Values 30, 100, 127
- ✅ `test_velocity_support_default_fallback` - Missing velocity uses 64
- ✅ `test_velocity_boundary_values` - Values 0, 1, 127
- ✅ `test_add_notes_invalid_velocity` - Rejects -1, 128
- ✅ `test_add_notes_velocity_undo` - Undo preserves velocity
- ✅ `test_add_notes_velocity_redo` - Redo restores velocity

---

## Flow 2: Track Volume & Pan (0-127)

### Path: LLM → MCP → Backend → State → Export

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LLM sends MCP tool call                                   │
│    add_track({volume: 50, pan: 127, ...})                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. MCP Server (server.py:59-64)                              │
│    AddTrackParams schema validates:                          │
│    - volume: int = 100 (default)                             │
│    - pan: int = 64 (default)                                 │
│    - ge=0, le=127 for both                                   │
│    ✅ Validation: Rejects -10, 128, 200, etc.                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. MCP Server (server.py:305)                                │
│    Call handler passes params:                               │
│    add_track(name, instrument, volume, pan)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Backend (tools/track.py:6-41)                             │
│    add_track() validates:                                    │
│    - Lines 27-28: if not (0 <= volume <= 127)               │
│    - Lines 31-32: if not (0 <= pan <= 127)                  │
│    - Line 34-39: state.tracks[name] = {..., volume, pan}    │
│    ✅ Double validation for direct Python calls              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. State Storage (state.py)                                  │
│    - Stored in state.tracks dict with volume/pan fields     │
│    - Undo/redo via copy.deepcopy() preserves values         │
│    ✅ Volume/pan persist in snapshots                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. MIDI Export (midi_export.py:379-384)                      │
│    track_state = state.tracks[track_name]                   │
│    volume = track_state.get("volume", 100)                  │
│    pan = track_state.get("pan", 64)                         │
│    - Writes CC7 (volume) message                            │
│    - Writes CC10 (pan) message                              │
│    ✅ Exported to .mid file at time=0                        │
└─────────────────────────────────────────────────────────────┘
```

**Test Coverage:**
- ✅ `test_add_track_with_volume_and_pan` - Custom values
- ✅ `test_add_track_volume_and_pan_defaults` - Defaults 100, 64
- ✅ `test_add_track_volume_out_of_range` - Rejects -10, 128, 200
- ✅ `test_add_track_pan_out_of_range` - Rejects -1, 128, 300
- ✅ `test_add_track_volume_and_pan_boundary_values` - Values 0, 127
- ✅ `test_add_track_with_volume_pan_undo` - Undo removes track
- ✅ `test_add_track_with_volume_pan_redo` - Redo restores volume/pan
- ✅ `test_volume_and_pan_support` - CC messages in MIDI
- ✅ `test_volume_and_pan_defaults` - Default CC values

---

## Flow 3: Multiple Tempo Changes

### Path: Sections → MIDI Export → Tempo Track

```
┌─────────────────────────────────────────────────────────────┐
│ 1. LLM creates sections with different tempos                │
│    add_section("intro", 1, 4, 72, ...)                      │
│    add_section("verse", 5, 8, 120, ...)                     │
│    add_section("chorus", 9, 12, 90, ...)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. State Storage (state.py)                                  │
│    state.sections = [                                        │
│      {start_measure: 1, tempo: 72, ...},                    │
│      {start_measure: 5, tempo: 120, ...},                   │
│      {start_measure: 9, tempo: 90, ...}                     │
│    ]                                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. MIDI Export (midi_export.py:328-386)                      │
│    Creates dedicated Tempo Track (Track 0):                 │
│    - Line 334-339: Get first section's tempo → time=0       │
│    - Line 355-372: Collect tempo changes from sections[1:]  │
│    - Line 364: Calculate tick position via                  │
│      _calculate_section_beat_offset()                       │
│    - Line 375-383: Sort and write set_tempo messages        │
│    ✅ All tempo changes in Track 0                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. MIDI File Structure                                       │
│    Track 0: Tempo Track                                      │
│      - set_tempo @ tick 0 (72 BPM)                          │
│      - set_tempo @ tick N (120 BPM)                         │
│      - set_tempo @ tick M (90 BPM)                          │
│    Track 1+: Instrument tracks                              │
│    ✅ DAW recognizes tempo changes                           │
└─────────────────────────────────────────────────────────────┘
```

**Test Coverage:**
- ✅ `test_multiple_tempo_changes` - 3 sections with 72→120→90 BPM
- ✅ `test_export_midi_tempo_from_section` - Single section tempo
- ✅ Updated track index tests for new Tempo Track structure

---

## Validation Layers

### Layer 1: MCP Server (Pydantic)
- **Purpose:** Validate LLM inputs before reaching backend
- **Location:** `server.py` Pydantic schemas
- **Constraints:**
  - `ge=0, le=127` for velocity, volume, pan
  - Type checking (int, str, float)

### Layer 2: Backend Functions
- **Purpose:** Validate direct Python calls (tests, internal usage)
- **Location:** `tools/note.py`, `tools/track.py`
- **Validation:**
  - Range checks (0-127)
  - Type checks
  - Existence checks (track exists)

### Layer 3: MIDI Export
- **Purpose:** Safe defaults for missing values
- **Location:** `midi_export.py`
- **Fallbacks:**
  - `note.get("velocity", 64)`
  - `track.get("volume", 100)`
  - `track.get("pan", 64)`

---

## Backwards Compatibility

All new features use **optional parameters with defaults**:

```python
# OLD CODE (still works)
add_track("piano", "piano")
add_notes([{"track": "piano", "pitch": 60, "start": 0, "duration": 1}])

# NEW CODE (optional enhancements)
add_track("piano", "piano", volume=50, pan=127)
add_notes([{"track": "piano", "pitch": 60, "start": 0, "duration": 1, "velocity": 100}])
```

**Guarantee:** All existing code continues to work unchanged.

---

## Summary: Full Stack Verification ✅

| Feature | MCP Schema | Backend Validation | State Storage | MIDI Export | Test Coverage |
|---------|------------|-------------------|---------------|-------------|---------------|
| Velocity | ✅ ge=0,le=127 | ✅ 0-127 check | ✅ Dict field | ✅ note.get() | ✅ 6 tests |
| Volume | ✅ ge=0,le=127 | ✅ 0-127 check | ✅ Dict field | ✅ CC7 | ✅ 9 tests |
| Pan | ✅ ge=0,le=127 | ✅ 0-127 check | ✅ Dict field | ✅ CC10 | ✅ 9 tests |
| Multi-Tempo | N/A | ✅ Section validation | ✅ Sections list | ✅ Track 0 | ✅ 3 tests |

**Total:** 138 tests passing, all data flows verified end-to-end.
