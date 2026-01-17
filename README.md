# MIDI Gen MCP

**MCP Server for AI-Integrated MIDI Generation**

A Model Context Protocol (MCP) server that provides low-level MIDI manipulation tools for AI-assisted music composition. This server exposes deterministic CRUD operations for MIDI generation, keeping all creative reasoning in the LLM (Claude).

## Features

- **19 MCP Tools** for MIDI manipulation (including harmony and validation tools)
- **Chord Progression Tracking** with automatic harmony validation
- **Expression Syntax** for precise timing (e.g., `"9 + 1/3"` for triplets)
- **General MIDI Support** (128 instrument mappings)
- **Multi-track MIDI Export** with automatic channel assignment
- **Undo/Redo** (up to 10 actions)
- **Section-based Structure** with tempo/time signature/key per section
- **Beat-based Timing** (quarter notes, time-signature agnostic)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/IrisMu01/midi-gen-mcp.git
cd midi-gen-mcp

# Install in development mode
pip install -e ".[dev]"
```

### Quick Setup

```bash
make install    # Install with dev dependencies
make test       # Run all tests
```

## Usage

### Running the MCP Server

The server communicates via stdio, designed for use with Claude Desktop or other MCP clients.

```bash
# Run the server directly
midi-gen-mcp

# Or with Python
python -m midi_gen_mcp.server
```

### Configure for Claude Desktop

Add to your Claude Desktop MCP settings (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "midi-gen": {
      "command": "midi-gen-mcp"
    }
  }
}
```

Or use the full Python path:

```json
{
  "mcpServers": {
    "midi-gen": {
      "command": "python",
      "args": ["-m", "midi_gen_mcp.server"]
    }
  }
}
```

## MCP Tools Reference

### Song Management

#### `set_title`
Set the title of the musical piece.

**Parameters:**
- `title` (string): The title for the piece

**Example:**
```json
{
  "title": "Moonlight Sonata"
}
```

#### `get_piece_info`
Get overview information about the current piece.

**Returns:**
- Title
- Sections overview
- Tracks list
- Total note count

---

### Structure Management

#### `add_section`
Add a new section to the piece with tempo, time signature, and key.

**Parameters:**
- `name` (string): Section name (must be unique)
- `start_measure` (int): Starting measure (1-indexed, ≥1)
- `end_measure` (int): Ending measure (inclusive, ≥start_measure)
- `tempo` (int): Tempo in BPM (1-300)
- `time_signature` (string): Time signature (e.g., "4/4", "6/8")
- `key` (string): Key signature (e.g., "C", "Am", "F#m")
- `description` (string, optional): Section description/notes

**Example:**
```json
{
  "name": "intro",
  "start_measure": 1,
  "end_measure": 4,
  "tempo": 72,
  "time_signature": "4/4",
  "key": "Dm",
  "description": "Sparse piano, melancholic mood"
}
```

#### `edit_section`
Edit an existing section. Automatically adjusts neighboring sections to prevent overlaps.

**Parameters:**
- `name` (string): Name of the section to edit
- `start_measure` (int, optional): New starting measure
- `end_measure` (int, optional): New ending measure
- `tempo` (int, optional): New tempo in BPM
- `time_signature` (string, optional): New time signature
- `key` (string, optional): New key signature
- `description` (string, optional): New description

#### `get_sections`
Get all sections in the piece, sorted by start_measure.

---

### Track Management

#### `add_track`
Add a new track to the piece.

**Parameters:**
- `name` (string): Track name (must be unique)
- `instrument` (string): Instrument name (see General MIDI mapping below)

**Example:**
```json
{
  "name": "piano",
  "instrument": "acoustic_grand_piano"
}
```

#### `remove_track`
Remove a track and all its notes.

**Parameters:**
- `name` (string): Name of the track to remove

#### `get_tracks`
Get all tracks in the piece.

---

### Note Operations

#### `add_notes`
Add multiple notes to the piece (batch operation).

**Parameters:**
- `notes` (array): List of note objects with:
  - `track` (string): Track name (must exist)
  - `pitch` (int): MIDI note number (0-127, where 60 = Middle C)
  - `start` (number or string): Start time in beats (quarter notes)
  - `duration` (number or string): Duration in beats

**Expression Syntax:**
Both `start` and `duration` support mathematical expressions for precise timing:
- `"1/3"` - Triplet eighth note
- `"9 + 1/3"` - Beat 9 plus one triplet
- `"2 * 3"` - 6 beats
- Simple numbers: `0`, `1.5`, `4`

**Example:**
```json
{
  "notes": [
    {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
    {"track": "piano", "pitch": 64, "start": "1 + 1/3", "duration": "1/3"},
    {"track": "violin", "pitch": 67, "start": 2, "duration": "1/2"}
  ]
}
```

#### `remove_notes_in_range`
Remove all notes in a track within a time range.

**Parameters:**
- `track` (string): Track name
- `start_time` (number): Start time in beats (inclusive)
- `end_time` (number): End time in beats (exclusive)

**Example:**
```json
{
  "track": "piano",
  "start_time": 0,
  "end_time": 4
}
```

#### `get_notes`
Query notes, optionally filtered by track and/or time range.

**Parameters:**
- `track` (string, optional): Filter by track name
- `start_time` (number, optional): Filter by start time (inclusive)
- `end_time` (number, optional): Filter by end time (exclusive)

---

### Harmony Tools

#### `add_chords`
Add chord progression to the piece. Validates chord symbols and returns chord tones for each chord.

**Parameters:**
- `chords` (array): List of chord objects with:
  - `beat` (number): Beat position where chord starts
  - `chord` (string): Chord symbol (e.g., "C", "Cm7", "G7", "Fmaj9")
  - `duration` (number): Duration of the chord in beats

**Returns:**
- `success` (boolean): Whether all chords were added successfully
- `chords_added` (array): List of added chords with their chord_tones
- `errors` (array): Any validation errors for invalid chord symbols

**Supported Chord Symbols:**
The server uses the `pychord` library for chord parsing. Common chord types include:
- Major: `C`, `D`, `F#`
- Minor: `Cm`, `Dm`, `Bbm`
- Dominant 7th: `C7`, `G7`, `D7`
- Major 7th: `Cmaj7`, `Fmaj7`
- Minor 7th: `Cm7`, `Dm7`
- Diminished: `Cdim`, `Bdim`
- Augmented: `Caug`
- Suspended: `Csus4`, `Dsus2`
- Extended: `C9`, `C11`, `C13`, `Cadd9`
- 6th chords: `C6`, `Cm6`

**Example:**
```json
{
  "chords": [
    {"beat": 0, "chord": "C", "duration": 4},
    {"beat": 4, "chord": "F", "duration": 4},
    {"beat": 8, "chord": "G7", "duration": 4},
    {"beat": 12, "chord": "C", "duration": 4}
  ]
}
```

**Overlap Behavior:**
When a later chord overlaps with an existing chord, the original chord is split and partially removed to make room for the new chord.

#### `get_chords_in_range`
Get all chords in a beat range.

**Parameters:**
- `start_beat` (number): Start of the beat range
- `end_beat` (number): End of the beat range

**Returns:**
Array of chord objects in the specified range.

**Example:**
```json
{
  "start_beat": 0,
  "end_beat": 8
}
```

#### `remove_chords_in_range`
Remove chords in a beat range. Also clears all flagged notes since harmony context becomes stale.

**Parameters:**
- `start_beat` (number): Start of the beat range
- `end_beat` (number): End of the beat range

---

### Validation Tools

#### `flag_notes`
Flag notes that fall outside the planned chord progression. Useful for detecting melody-harmony conflicts.

**Parameters:**
- `tracks` (array of strings): List of track names to check
- `start_beat` (number): Start of the beat range
- `end_beat` (number): End of the beat range

**Returns:**
- `flagged_count` (number): Number of notes flagged
- `message` (string): Status message

**Behavior:**
- Auto-clears all previous flags first
- For each note in the specified tracks and range:
  - Finds the active chord at the note's start beat
  - Checks if the note's pitch class matches the chord tones
  - Flags the note if it doesn't match (sets `flagged: true`)
- Notes in gaps (where no chord exists) are NOT flagged (missing harmony is not an error)

**Example:**
```json
{
  "tracks": ["melody", "piano"],
  "start_beat": 0,
  "end_beat": 16
}
```

#### `remove_flagged_notes`
Remove all flagged notes from the piece.

**Returns:**
- `removed_notes` (array): List of removed notes with track, pitch, start, duration
- `count` (number): Number of notes removed

**Self-Correction Workflow Example:**

1. Add melody and chord progression
2. Flag notes that don't fit the harmony: `flag_notes(["melody"], 0, 16)`
3. Review flagged notes: `get_notes("melody", 0, 16)` (look for `flagged: true`)
4. Remove problematic notes: `remove_flagged_notes()`
5. Add corrected notes: `add_notes([...])`
6. Verify: `flag_notes(["melody"], 0, 16)` (should return 0)

---

### Utility

#### `undo`
Undo the last action. Supports up to 10 undo steps.

#### `redo`
Redo the last undone action.

#### `export_midi`
Export the current piece to a MIDI file.

**Parameters:**
- `filepath` (string): Path to save the MIDI file (will add `.mid` if missing)

**Example:**
```json
{
  "filepath": "my_composition.mid"
}
```

**MIDI Export Features:**
- Expression evaluation (converts `"9 + 1/3"` to exact ticks)
- Multi-track support (one MIDI track per instrument)
- Automatic channel assignment (drums on channel 9)
- Tempo and time signature from sections
- General MIDI instrument mapping
- 480 ticks per beat (standard resolution)
- Fixed velocity: 64 (medium)

---

## General MIDI Instrument Mapping

The server supports 128 General MIDI instruments. Common examples:

**Piano (0-7):**
- `piano`, `acoustic_grand_piano` → 0
- `bright_acoustic_piano` → 1
- `electric_piano_1` → 4
- `harpsichord` → 6

**Strings (40-47):**
- `violin` → 40
- `viola` → 41
- `cello` → 42
- `harp` → 46

**Brass (56-63):**
- `trumpet` → 56
- `trombone` → 57
- `french_horn` → 60

**Woodwinds:**
- `flute` → 73
- `clarinet` → 71
- `saxophone` → 64

**Bass (32-39):**
- `bass`, `acoustic_bass` → 32
- `electric_bass_finger` → 33
- `synth_bass_1` → 38

**Guitars (24-31):**
- `guitar`, `acoustic_guitar_nylon` → 24
- `electric_guitar_clean` → 27
- `distortion_guitar` → 30

**Percussion:**
- `drums`, `percussion` → Channel 9 (GM percussion)

For the complete list, see `src/midi_gen_mcp/midi_export.py`.

**Note:** Unknown instruments default to piano (0).

---

## State Schema

The server maintains an in-memory state with the following structure:

```python
{
  "title": str,                    # Piece title (default: "Untitled")
  "tracks": {                      # Track dictionary
    "track_name": {
      "name": str,
      "instrument": str
    }
  },
  "notes": [                       # Flat list of notes
    {
      "track": str,
      "pitch": int,                # 0-127 (60 = Middle C)
      "start": str | float,        # Beats, supports expressions
      "duration": str | float,     # Beats, supports expressions
      "flagged": bool              # Optional, set by flag_notes tool
    }
  ],
  "sections": [                    # Section list (sorted by start_measure)
    {
      "name": str,
      "start_measure": int,
      "end_measure": int,
      "tempo": int,
      "time_signature": str,
      "key": str,
      "description": str
    }
  ],
  "chord_progression": [           # Chord progression (sorted by beat)
    {
      "beat": float,
      "chord": str,
      "duration": float,
      "chord_tones": list[str]     # Pitch classes (e.g., ["C", "E", "G"])
    }
  ],
  "undo_stack": list,              # Max 10 state snapshots
  "redo_stack": list               # Cleared on new actions
}
```

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_note.py

# Using Make
make test
```

**Test Coverage:**
- 116 tests across 8 test modules
- State management (8 tests)
- Song tools (4 tests)
- Structure tools (13 tests)
- Track tools (9 tests)
- Note operations (17 tests)
- MIDI export (20 tests)
- Chord parser (16 tests)
- Harmony tools (18 tests)
- Validation tools (13 tests)

### Project Structure

```
midi-gen-mcp/
├── src/
│   └── midi_gen_mcp/
│       ├── __init__.py
│       ├── server.py           # MCP server entry point
│       ├── state.py            # In-memory state management
│       ├── midi_export.py      # MIDI file generation
│       ├── chord_parser.py     # Chord symbol parsing (pychord wrapper)
│       └── tools/              # Tool implementations
│           ├── __init__.py
│           ├── song.py         # set_title, get_piece_info
│           ├── structure.py    # add_section, edit_section, get_sections
│           ├── track.py        # add_track, remove_track, get_tracks
│           ├── note.py         # add_notes, remove_notes_in_range, get_notes
│           ├── harmony.py      # add_chords, get_chords_in_range, remove_chords_in_range
│           ├── validation.py   # flag_notes, remove_flagged_notes
│           └── utility.py      # undo, redo, export_midi
├── tests/
│   ├── test_state.py
│   ├── test_song.py
│   ├── test_structure.py
│   ├── test_track.py
│   ├── test_note.py
│   ├── test_midi_export.py
│   ├── test_chord_parser.py
│   ├── test_harmony_tools.py
│   └── test_validation_tools.py
├── pyproject.toml
├── Makefile
├── README.md
├── PLANNING.md
└── DESIGN_DOC.md
```

---

## Design Philosophy

**Key Principle:** MCP tools are deterministic operations only. All music theory, composition decisions, and creative reasoning happen in the LLM (Claude).

**What the MCP server does:**
- ✅ CRUD operations for notes, tracks, sections
- ✅ MIDI file export
- ✅ State management (undo/redo)
- ✅ Data validation

**What the MCP server does NOT do:**
- ❌ Generate melodies or harmonies
- ❌ Make compositional decisions
- ❌ Apply music theory rules
- ❌ Dynamic expression (velocity is fixed at 64)

The LLM uses these low-level tools to compose music by calling them in sequence with creative intent.

---

## Example Workflow

Here's how Claude might compose a simple melody:

1. **Create structure:**
   ```
   add_section("intro", 1, 4, 120, "4/4", "C")
   ```

2. **Add tracks:**
   ```
   add_track("piano", "piano")
   add_track("bass", "acoustic_bass")
   ```

3. **Compose melody:**
   ```
   add_notes([
     {"track": "piano", "pitch": 60, "start": 0, "duration": 1},
     {"track": "piano", "pitch": 64, "start": 1, "duration": 1},
     {"track": "piano", "pitch": 67, "start": 2, "duration": 1},
     {"track": "piano", "pitch": 72, "start": 3, "duration": 1}
   ])
   ```

4. **Add bass line:**
   ```
   add_notes([
     {"track": "bass", "pitch": 48, "start": 0, "duration": 4}
   ])
   ```

5. **Export:**
   ```
   export_midi("my_composition.mid")
   ```

---

## Limitations

- **No dynamic expression:** All notes use fixed velocity (64)
- **No articulations:** No staccato, legato, or other performance markings
- **No pitch bend or modulation:** MIDI CC messages not supported
- **No audio rendering:** Exports MIDI only (use external DAW for playback)
- **In-memory only:** State is not persisted between sessions
- **Single tempo per section:** No gradual tempo changes within sections

---

## Future Enhancements

Potential future additions (not in current scope):

- [ ] Velocity dynamics per note
- [ ] MIDI CC messages (modulation, sustain, expression)
- [ ] Pitch bend support
- [ ] Save/load session to JSON
- [ ] Real-time MIDI output
- [ ] Audio rendering (soundfont-based)

---

## License

See repository for license information.

---

## Related Documentation

- [PLANNING.md](PLANNING.md) - Implementation planning and progress
- [DESIGN_DOC.md](DESIGN_DOC.md) - Overall system design
- [MCP Documentation](https://modelcontextprotocol.io/) - Model Context Protocol

---

## Contributing

This is the **Core Component #1: MCP Server** from the overall project. For information about the complete system (including music theory skills and frontend), see `DESIGN_DOC.md`.

---

**Status:** Core MCP server complete with 116 passing tests. All features including harmony and validation tools implemented. Ready for integration with Claude Desktop.
