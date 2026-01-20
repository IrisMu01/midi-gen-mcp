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

## Out of Scope (PoC Stage)

**Not implementing yet:**
- CC11 (Expression) - Requires time-varying automation infrastructure, mainly for orchestral libraries
- CC1 (Modulation), CC64 (Sustain pedal) - Less critical for basic composition
- Articulation mapping - Complex, DAW-specific
- Time-varying automation curves - Future feature for UI phase
- Electron frontend - Deferred until MIDI quality validated

---

## Success Criteria

- [ ] Tempo changes work across multiple sections
- [ ] Velocity per-note controls dynamics
- [ ] Volume/pan per-track exports to DAW mixer
- [ ] All changes are backwards compatible (optional parameters)
- [ ] Existing tests pass, new tests added for new features

---

## Future Considerations

### Velocity vs Volume vs Expression (Reference)
- **Velocity** (note-on): Per-note attack, affects volume AND timbre (good libraries)
- **CC7 (Volume)**: Per-track mixer level, affects all notes equally, pure amplitude
- **CC10 (Pan)**: Stereo positioning (0=left, 64=center, 127=right)
- **CC11 (Expression)**: Secondary dynamic control for phrase-level crescendos/diminuendos, commonly used in orchestral libraries

**PoC Priority:** Velocity (essential) > Volume/Pan (useful) > Expression (niche, needs automation)

---

## Notes

Current focus: **MIDI export quality improvements** for PoC evaluation. Goal is to export high-quality MIDI that sounds good in professional DAWs, not to build UI/frontend yet.
