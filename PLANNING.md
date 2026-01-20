# Planning Document

This file tracks current implementation priorities for the MCP server.

---

## Current Status

The MCP server is functionally complete with:
- Core MIDI composition tools (song, structure, track, note operations)
- Chord progression tracking with validation tools
- Expression evaluation for note timing
- MIDI export with General MIDI instrument mapping
- Undo/redo support

See `DESIGN_DOC.md` for architecture and `README.md` for usage.

---

## Current PoC Stage: MIDI Quality Focus

**Goal:** Improve MIDI export quality for evaluation in professional DAWs (Logic, Ableton, MuseScore).

**Philosophy:** No frontend UI yet. Export to existing DAWs for listening/testing. Validate core composition quality before building interface.

---

## Priority Tasks

### Task 1: Fix Tempo Change Bug

**Problem:** Only the first section's tempo is exported. Tempo changes after bar 1 are ignored.

**Root Cause (midi_export.py:379-387):**
```python
# Only reads first section's tempo
if state.sections:
    tempo = state.sections[0].get("tempo", 120)
else:
    tempo = 120

# Only writes tempo at time=0
midi_track.append(mido.MetaMessage("set_tempo", tempo=microseconds_per_beat, time=0))
```

**Solution:**
1. Collect tempo changes from all sections (sorted by start_measure)
2. Calculate tick position for each section's start using `_calculate_section_beat_offset()`
3. Insert `set_tempo` meta messages at the correct tick positions
4. Mix tempo events into the event stream alongside note events
5. Convert to delta times during final MIDI track assembly

**Design Decision:** Create tempo events per-track (current approach) OR create a dedicated tempo track (track 0). Tempo track is cleaner for multi-track MIDI files.

**Files to modify:**
- `src/midi_gen_mcp/midi_export.py`

**Testing:**
- Create piece with 3+ sections, different tempos (e.g., 72 → 120 → 90 BPM)
- Export MIDI, import into Logic/Ableton
- Verify tempo changes occur at correct measures

**Undo/Redo Compatibility:**
- Tempo is already part of section dict, which is captured in `state.sections`
- `snapshot_state()` already includes sections via `copy.deepcopy(state.sections)`
- No changes needed - existing undo/redo handles tempo changes

---

### Task 2: Add Velocity Support

**Motivation:** Essential for expressive/realistic MIDI. Currently all notes hardcoded to velocity 64 (medium).

**Changes:**

#### 2a. Note Schema
Add optional `velocity` field (0-127, default 64):
```python
{
    "track": "piano",
    "pitch": 60,
    "start": 0,
    "duration": 1,
    "velocity": 80  # NEW: optional
}
```

#### 2b. Update MCP Tools
**File:** `src/midi_gen_mcp/tools/notes.py`
- `add_notes()`: Accept `velocity` in note dicts (optional)
- No breaking changes (defaults to 64 if not provided)

**Note:** No changes needed to `state.py` - velocity is already part of note dict, undo/redo already captures it

#### 2c. Update MIDI Export
**File:** `src/midi_gen_mcp/midi_export.py` (line 422)
```python
# Replace:
"velocity": DEFAULT_VELOCITY,

# With:
"velocity": note.get("velocity", DEFAULT_VELOCITY),
```

**Testing:**
- Add notes with varying velocities (30, 64, 100, 127)
- Export MIDI, check velocity values in DAW piano roll
- Verify default (64) works when velocity not specified

---

### Task 3: Add Track Volume & Pan (CC Messages)

**Motivation:** Enable basic mixing control. Initial volume/pan settings exported to MIDI as CC7/CC10 messages.

**Implementation:**

#### 3a. Track Schema
**File:** `src/midi_gen_mcp/state.py`
```python
# tracks dict values now include:
{
    "name": "piano",
    "instrument": "acoustic_grand_piano",
    "volume": 100,  # NEW: CC7 (0-127, default 100)
    "pan": 64       # NEW: CC10 (0=left, 64=center, 127=right, default 64)
}
```

#### 3b. Update add_track Tool
**File:** `src/midi_gen_mcp/tools/tracks.py`
```python
def add_track(
    name: str,
    instrument: str,
    volume: int = 100,  # NEW
    pan: int = 64       # NEW
) -> str:
```

**Validation:**
- Volume: 0-127 (MIDI valid range)
- Pan: 0-127 (0=hard left, 64=center, 127=hard right)
- Return error message if values out of range

**Undo/Redo Compatibility:**
- Verify `state.py` `snapshot_state()` and `restore_state()` already handle tracks dict
- Track dict values (including new volume/pan fields) are captured in snapshots via `copy.deepcopy()`
- No changes needed - existing undo/redo infrastructure handles arbitrary track fields

#### 3c. Update MIDI Export
**File:** `src/midi_gen_mcp/midi_export.py` (after line 377)

After `program_change`, insert CC messages:
```python
track_state = state.tracks[track_name]
volume = track_state.get("volume", 100)
pan = track_state.get("pan", 64)

# Insert at time=0
midi_track.append(mido.Message("control_change", control=7, value=volume, channel=channel, time=0))
midi_track.append(mido.Message("control_change", control=10, value=pan, channel=channel, time=0))
```

**Testing:**
- Create tracks with volume=50, pan=0 (hard left)
- Create tracks with volume=127, pan=127 (hard right)
- Export MIDI, check mixer settings in DAW

---

## Test Cases

### Valid Input Tests
- [ ] Velocity values: 0, 1, 64, 127 (boundary and typical values)
- [ ] Volume values: 0, 50, 100, 127
- [ ] Pan values: 0 (hard left), 64 (center), 127 (hard right)
- [ ] Multiple tempo sections: 60 → 120 → 90 BPM across 3+ sections
- [ ] Notes with and without explicit velocity (test default fallback)

### Undo/Redo Compatibility Tests
- [ ] Add note with velocity=100, undo, verify note removed
- [ ] Add note with velocity=100, redo, verify velocity preserved
- [ ] Add track with volume=50, pan=127, undo, verify track removed
- [ ] Add track with volume=50, pan=127, redo, verify volume/pan preserved
- [ ] Add section with tempo=90, undo, verify section removed
- [ ] Modify track volume from 100 to 50, undo, verify restored to 100
- [ ] Complex workflow: add track → add notes → modify tempo → undo×3 → redo×2, verify state consistency

### Invalid Input Tests (Expect MCP Server Errors)
- [ ] Velocity out of range: -1, 128, 256, 1000
- [ ] Volume out of range: -10, 128, 200
- [ ] Pan out of range: -1, 128, 300
- [ ] Tempo invalid: 0, -60, 1000 BPM (too slow/fast)
- [ ] Invalid time signature strings: "4", "4/", "/4", "0/4", "4/0"
- [ ] Invalid note pitch: -1, 128 (MIDI valid range is 0-127)
- [ ] Invalid expression syntax: "1 + + 2", "garbage", "import os"
- [ ] Track operations on non-existent tracks
- [ ] Section operations with invalid measure ranges (start > end, start < 1)

### Edge Cases
- [ ] Velocity = 0 (note off via note-on with velocity 0, valid MIDI)
- [ ] Volume = 0 (silent track, valid)
- [ ] Tempo changes on same measure as previous section ends
- [ ] Overlapping sections with different time signatures
- [ ] Very large files: 10,000+ notes across 50+ sections (programmatically generated via loops to test performance and MIDI export scalability)

---

## Success Criteria

- [ ] Tempo changes work across multiple sections
- [ ] Velocity per-note controls dynamics
- [ ] Volume/pan per-track exports to DAW mixer
- [ ] All changes are backwards compatible (optional parameters)
- [ ] Existing tests pass, new tests added for new features
- [ ] Invalid inputs return clear error messages (not crashes)
- [ ] Error messages specify valid ranges (e.g., "velocity must be 0-127, got 200")
- [ ] Undo/redo correctly captures and restores velocity, volume, pan, and tempo changes
- [ ] Undo/redo snapshots maintain full state consistency across all new features
