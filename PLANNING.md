# Planning Document

This file is for planning future implementation changes and features.

---

## Current Status

The MCP server implementation is complete with all core features:
- 14 MCP tools across 5 categories (song, structure, track, note, utility)
- Expression evaluation for note timing (e.g., "9 + 1/3")
- MIDI export with General MIDI instrument mapping
- Undo/redo with 10-snapshot limit
- 71 passing unit tests

See `DESIGN_DOC.md` for full architecture and `README.md` for usage.

---

## Planned Feature: Explicit Chord Progression Tracking + Self-Correction

### Motivation

Current observations from testing:
1. Claude plans chord progressions in section descriptions but executes differently (planned F6/9, wrote Cadd11)
2. Harmony details buried in free-form text → LLM doesn't consistently reference them
3. No verification mechanism to catch melody-harmony conflicts

### Solution: First-Class Harmony State + Validation Tools

Make chord progression a **tracked, queryable data structure** with **self-correction workflow**.

---

## Implementation Plan

### Task 1: Extend State Schema

**File:** `src/midi_gen_mcp/state.py`

**Changes:**
```python
@dataclass
class State:
    title: str
    tracks: dict[str, dict[str, Any]]
    notes: list[dict[str, Any]]  # NEW: notes can have optional "flagged": bool field
    sections: list[dict[str, Any]]
    chord_progression: list[dict[str, Any]]  # NEW: [{beat, chord, duration, chord_tones}]
    undo_stack: list[dict[str, Any]]
    redo_stack: list[dict[str, Any]]
```

**Update:**
- `snapshot_state()` to include `chord_progression`
- `restore_state()` to restore `chord_progression`

---

### Task 2: Chord Parser Module

**New File:** `src/midi_gen_mcp/chord_parser.py`

**Purpose:** Wrapper around `pychord` library with error handling

**Key Functions:**
```python
def parse_chord_symbol(symbol: str) -> dict:
    """
    Parse chord symbol and return chord tones.

    Args:
        symbol: Chord symbol string (e.g., "Cm7", "G7", "Fmaj9")

    Returns:
        {
            "chord": str,           # Original symbol
            "chord_tones": List[str]  # Pitch classes ["C", "E", "G", "Bb"]
        }

    Raises:
        ValueError: If chord symbol not recognized by pychord
    """

def get_supported_qualities() -> List[str]:
    """Return list of supported chord qualities for error messages."""
```

**Dependencies:** Add `pychord` to `pyproject.toml`

**Error Handling:**
- If chord symbol not recognized, raise `ValueError` with:
  - Invalid symbol
  - List of supported qualities (from pychord constants)
  - Examples: ["C", "Cm", "C7", "Cmaj7", "Cdim", "Caug", "Csus4", "C9", "C13"]

**Enharmonics:** Use whatever pychord returns (C# vs Db), document this behavior

---

### Task 3: Harmony Tools

**New File:** `src/midi_gen_mcp/tools/harmony.py`

**Tools (3 total):**

#### 1. `add_chords`
```python
def add_chords(chords: List[dict]) -> dict:
    """
    Add chord progression to the piece.

    Args:
        chords: List of {beat: float, chord: str, duration: float}

    Returns:
        {
            "success": bool,
            "chords_added": List[{beat, chord, duration, chord_tones}],
            "errors": List[{invalid_chord, error, supported_qualities}] (if any)
        }

    Behavior:
        - Validates each chord symbol using chord_parser
        - If all valid: adds to state.chord_progression, returns success
        - If any invalid: returns error with helpful message, state unchanged
    """
```

#### 2. `get_chords_in_range`
```python
def get_chords_in_range(start_beat: float, end_beat: float) -> List[dict]:
    """
    Get all chords in a beat range.

    Returns: List[{beat, chord, duration, chord_tones}]
    """
```

#### 3. `remove_chords_in_range`
```python
def remove_chords_in_range(start_beat: float, end_beat: float) -> str:
    """
    Remove chords in a beat range.

    Side effects:
        - Clears ALL flagged notes (harmony context is now stale)

    Returns: Confirmation message
    """
```

---

### Task 4: Validation Tools

**New File:** `src/midi_gen_mcp/tools/validation.py`

**Tools (2 total):**

#### 1. `flag_notes`
```python
def flag_notes(tracks: List[str], start_beat: float, end_beat: float) -> int:
    """
    Flag notes that fall outside the planned chord progression.

    Args:
        tracks: Which tracks to check (e.g., ["piano", "bass"])
        start_beat, end_beat: Beat range

    Returns:
        Number of notes flagged

    Behavior:
        - Auto-clears ALL previous flags first
        - For each note in range:
          - Find active chord at note's start beat
          - Check if note's pitch is in chord_tones
          - If not, set note["flagged"] = True
        - Returns count of flagged notes

    Error handling:
        - If no chord_progression defined: return error
        - If note's beat has no active chord: flag it (missing harmony)
    """
```

#### 2. `remove_flagged_notes`
```python
def remove_flagged_notes() -> List[dict]:
    """
    Remove all flagged notes from state.

    Returns:
        List of removed notes (using standard note schema)
        [{track, pitch, start, duration}]

    Side effects:
        - Removes notes where flagged=True
        - No need to clear flagged field (notes are deleted)
    """
```

---

### Task 5: Tool Registration

**File:** `src/midi_gen_mcp/server.py`

**Register 5 new tools:**
- `add_chords` (harmony.py)
- `get_chords_in_range` (harmony.py)
- `remove_chords_in_range` (harmony.py)
- `flag_notes` (validation.py)
- `remove_flagged_notes` (validation.py)

**Total tool count:** 14 → 19 tools

---

### Task 6: Tests

**New Files:**
- `tests/test_chord_parser.py` (15 tests)
- `tests/test_harmony_tools.py` (20 tests)
- `tests/test_validation_tools.py` (15 tests)

**Coverage:**

#### Chord Parser Tests (15)
- Valid chord symbols (major, minor, 7th, maj7, dim, aug, sus, 9, 11, 13, add9)
- Invalid chord symbols (error handling)
- Enharmonic equivalents (C# vs Db)
- Edge cases (empty string, special characters)

#### Harmony Tools Tests (20)
- `add_chords`: valid symbols, invalid symbols, batch operations
- `add_chords`: overlapping chord ranges (later takes precedence)
- `get_chords_in_range`: normal range, empty range, partial overlap
- `remove_chords_in_range`: removes chords, clears flags
- Undo/redo with chord operations

#### Validation Tools Tests (15)
- `flag_notes`: notes in chord (not flagged)
- `flag_notes`: notes outside chord (flagged)
- `flag_notes`: multiple tracks
- `flag_notes`: auto-clears previous flags
- `flag_notes`: error when no chord progression
- `remove_flagged_notes`: returns correct schema
- `remove_flagged_notes`: only removes flagged notes
- Integration: flag → remove → add → verify

**Target:** All 101 tests passing (71 existing + 30 new)

---

### Task 7: Documentation

#### Update README.md
- Add "Harmony Tools" section with examples
- Add "Validation Tools" section with self-correction workflow
- Document supported chord symbols (link to pychord)
- Add example: melody → chords → harmonize → validate → fix

#### Update DESIGN_DOC.md
- Add harmony tools to tool categories
- Update compositional workflow (add chord planning phase)
- Update context window estimates (chord progression ~500 tokens)

---

### Task 8: Edge Cases & Design Decisions

#### Chord Overlap Behavior
```python
add_chords([
    {"beat": 0, "chord": "C7", "duration": 8},
    {"beat": 4, "chord": "F7", "duration": 4}  # Overlaps beats 4-8
])
```
**Decision:** Overlapping calls are allowed. When a later chord overlaps with an existing chord, the original longer chord should be split and partially removed to make room for the later chord. The later chord takes precedence in the overlapping region.

#### Missing Chord at Beat
```python
# Chords: C7 at beat 0-4, G7 at beat 8-12
# Note at beat 6 (gap!)
flag_notes(["melody"], 0, 16)
```
**Decision:** Missing harmony is NOT an error. If chords are missing in a section, no notes in that section will be flagged. Only notes that fall within an active chord's duration will be checked for harmony conflicts.

#### Enharmonic Normalization
**Decision:** Use pychord's default (no custom enharmonic logic). Document that C# and Db are distinct.

#### Multiple Tracks in `flag_notes`
```python
flag_notes(["melody", "piano", "bass"], 0, 16)
```
**Decision:** Flag notes across all specified tracks (useful for checking full arrangement)

---

### Task 9: Integration Testing

**Manual Test Scenarios:**

1. **Happy Path: Melody → Harmony**
   - Add melody
   - Plan chords with `add_chords`
   - Verify with `flag_notes` (expect 0)
   - Add harmony notes

2. **Self-Correction Path:**
   - Add melody with intentional wrong note
   - Plan chords
   - Flag notes (expect >0)
   - Remove flagged notes
   - Add corrected notes
   - Re-flag (expect 0)

3. **Chord Change Invalidates Flags:**
   - Add melody
   - Plan chords (Cm7)
   - Flag notes (some flagged)
   - Change chord to C7
   - Verify flags were auto-cleared

4. **Undo/Redo with Chords:**
   - Add chords
   - Add notes
   - Flag notes
   - Undo (chords removed, flags cleared)
   - Redo (chords restored)

---

### Task 10: Migration Path

**Backwards Compatibility:**
- Existing compositions have no chord_progression → empty list
- Existing tools (add_notes, etc.) work unchanged
- New tools are optional (old workflow still valid)

**No Breaking Changes:**
- State schema only adds fields, doesn't modify existing ones
- Undo/redo snapshots include new fields (old snapshots compatible via default values)

---

## Success Criteria

- [ ] All 101 tests passing (71 existing + 30 new)
- [ ] pychord dependency installed and working
- [ ] Invalid chord symbols return helpful error messages
- [ ] `flag_notes` correctly identifies non-harmonic notes
- [ ] Self-correction workflow (flag → remove → fix) works end-to-end
- [ ] Undo/redo preserves chord_progression state
- [ ] Skill documentation teaches workflow without being prescriptive
- [ ] README examples demonstrate typical usage

---

## Future Enhancements (Not in Scope)

- Jazz chord extensions (alt, #9, b13) via manual parser
- Chord symbol suggestions when invalid symbol provided
- Auto-suggest chord progression based on melody
- Visualize chord progression in frontend (chord chart above piano roll)
- Strictness levels for `flag_notes` (allow passing tones, neighbor tones)

---

## Notes

Current focus: **Explicit chord tracking + self-correction workflow** to address observed LLM harmonization errors.

Principle: Keep tools deterministic. Chord parsing is deterministic (pychord). Validation is deterministic (note in chord_tones or not). Creative decisions (which chords, which voicings) stay in LLM + skills.
