# AI-Integrated DAW: Technical Design Document

## Executive Summary

This document outlines the design of an AI-integrated Digital Audio Workstation (DAW) that uses LLM reasoning with low-level CRUD tools to generate symbolic music (MIDI), as an alternative to end-to-end tokenized generation approaches.

**Key Insight:** Instead of training models to output MIDI tokens directly, leverage LLM reasoning abilities with explicit music theory knowledge (skills) and deterministic DAW operations (MCP tools) to achieve more controllable, explainable, and potentially more musical outputs.

---

## Background & Motivation

### Current Approaches (MIDI-LLM, Text2Midi)
- **Method:** Fine-tune LLMs on text-MIDI pairs, expand vocabulary with MIDI tokens, generate sequences autoregressively
- **Strengths:** Fast generation (MIDI-LLM: 10s for 2K-token sequences at batch size 1), learns implicit patterns from training data
- **Limitations:** Generated music often lacks musical coherence to human listeners, opaque decision-making, difficult to edit or iterate

### Problem Statement
Tokenized generation has not yet achieved satisfactory musical quality despite benchmark improvements. The gap between what metrics measure and what sounds good remains significant.

---

## Design Goals

1. **Musical coherence:** Produce MIDI that sounds good to human listeners through explicit musical reasoning
2. **Explainability:** Make compositional decisions transparent via "composer's journal"
3. **Editability:** Support iterative refinement and human-AI collaboration
4. **Controllability:** Give users precise control over musical attributes without fighting the model
5. **Efficiency:** Manage context window and token usage for complex pieces (as an arbitrary example: compositions with 4000+ notes)

---

## System Architecture

### High-Level Overview

```
User Input (text prompt)
    ↓
Claude Sonnet 4.5 (via API)
    ├─→ Reads: Music theory skills
    ├─→ Reasons: Musical decisions (harmony, melody, rhythm, orchestration)
    └─→ Executes: MCP tool calls (CRUD operations)
         ↓
MCP Server (Python)
    ├─→ Maintains: In-memory song state (tracks, notes, sections, journal)
    └─→ Returns: Confirmation/current state
         ↓
Frontend DAW (Electron + React)
    ├─→ Displays: Chat, piano roll, tracks
    └─→ Enables: Playback, manual editing, export
```

### Key Design Principle

**MCP tools are deterministic CRUD operations only.** All creative work happens in the LLM through reasoning over skills. This ensures transparency and maintains the LLM as the single creative agent.

---

## Core Components

### 1. MCP Server (DAW Backend)

**Purpose:** Expose low-level music manipulation operations as tools Claude can call.

**Technology:**
- Language: Python
- Libraries: `mcp` (Anthropic SDK), `mido` (MIDI handling)
- State: In-memory data structures (dict/list), persisted as JSON or MIDI export

**Tool Categories:**

#### Song Management
```python
set_title(title: str)
get_piece_info() -> {title, num_sections, num_tracks, num_notes, sections[], tracks[]}
```

#### Structure Management
```python
add_section(name: str, start_measure: int, end_measure: int, tempo: int, time_signature: str, key: str, description: str)
edit_section(name: str, **kwargs)  # Auto-adjusts neighbors to prevent overlaps
get_sections() -> List[{name, start_measure, end_measure, tempo, time_signature, key, description}]
```

#### Track Management
```python
add_track(name: str, instrument: str)
remove_track(name: str)
get_tracks() -> List[{name, instrument}]
```

#### Note Operations (Core CRUD)
```python
add_notes(notes: List[{track, pitch, start, duration}])  # start/duration support expressions like "9 + 1/3"
remove_notes_in_range(track: str, start_time: float, end_time: float)
get_notes(track: str, start_time: float, end_time: float) -> List[notes]
```

#### Utility
```python
undo_last_action()
redo_last_action()
export_midi(filepath: str)
```

**Why low-level only:**
- Keeps tools deterministic (no hidden creativity)
- Makes compositional reasoning explicit (via section descriptions)
- Enables debugging and iteration
- Avoids "magic" operations like `harmonize_melody(style="jazz")`

**Note:** There is no separate journal - section descriptions serve both planning and execution notes.

### 2. Skills (Music Theory Knowledge)

**Purpose:** Provide LLM with musical vocabulary, principles, and context without prescriptive formulas.

**Structure:**
```
/mnt/skills/user/
├── music-theory/
│   ├── harmony/
│   │   ├── intervals.md (consonance, dissonance, tension-resolution)
│   │   ├── chord-construction.md (triads, extensions, alterations, voicings)
│   │   ├── voice-leading.md (smooth motion, contrary motion, voice independence)
│   │   └── functional-harmony.md (tonic-dominant relationships, cadences, modulation)
│   ├── melody/
│   │   ├── contour.md (arch shapes, climax points, stepwise vs. leaps)
│   │   ├── motif-development.md (repetition, sequence, fragmentation, augmentation)
│   │   └── phrase-structure.md (antecedent-consequent, periods, cadential patterns)
│   └── rhythm/
│       ├── meter-feel.md (duple vs. triple, strong-weak patterns, groove)
│       ├── syncopation.md (off-beat accents, anticipation, displaced accents)
│       └── rhythmic-motifs.md (ostinato, hemiola, polyrhythm)
├── genres/
│   ├── baroque.md (functional harmony, counterpoint, ornamentation, figured bass)
│   ├── classical.md (periodic phrasing, alberti bass, sonata form, balanced proportions)
│   ├── romantic.md (extended harmony, chromaticism, rubato, programmatic elements)
│   └── jazz-big-band.md (swing rhythm, extended chords, improvisation, section writing)
└── instrumentation/
    ├── piano.md (voicing, register, pedaling, stride bass)
    ├── strings.md (violin, cello: bowing, double stops, harmonics, pizzicato)
    ├── brass.md (trumpet, trombone: lip trills, mutes, section blend)
    ├── woodwinds.md (flute, clarinet: breathing, tonguing, timbral variety)
    └── drums.md (groove patterns, fills, cymbal work, dynamic shaping)
```

**Content Philosophy:**

✅ **DO Include:**
- Principles and their effects ("descending bass lines evoke melancholy")
- Multiple options ("tension can be created via A, B, or C")
- Context and trade-offs ("dense textures work for climax but mask melody")
- Genre conventions ("Baroque favors functional harmony, less chromaticism")
- Instrumentation ranges and voicing techniques

❌ **DON'T Include:**
- Step-by-step formulas ("intro: 4 bars, verse: 8 bars")
- Rigid rules ("always resolve leading tone up")
- Prescriptive recipes ("sad songs must use i-VI-III-VII")
- Generic templates to fill in

**Balance:** Teach "why" (principles), not "what" (formulas). Claude should understand musical language and compose original sentences, not rearrange pre-written paragraphs.

### 3. Frontend DAW

**Purpose:** Provide chat interface, visualization, playback, and manual editing capabilities.

**Technology (Recommended):**
- Framework: Electron (desktop app)
- UI: React or Svelte
- Piano Roll: `react-piano-component` or custom Canvas/SVG
- Playback: Tone.js (browser synthesis)
- Chat: Standard chat UI component

**Features (Prototype Scope):**
- Chat panel for user input and Claude responses
- Track list (show/hide/select)
- Piano roll visualization with quantization
- Transport controls (play/pause/stop)
- Manual note editing (add/remove/move notes)
- Export MIDI file

**Out of Scope (Prototype):**
- MIDI velocity/expression/articulation
- Automation curves
- Plugin support
- Per-track volume/pan
- Multiple song directory (single song for prototype)

**Architecture:**
```
Frontend (React)
    ├── ChatPanel: User input → Anthropic API
    ├── TrackList: Display tracks from MCP state
    ├── PianoRoll: Visualize notes, enable manual editing
    └── Transport: Playback with Tone.js

Backend Bridge (Node.js/Python)
    └── Relay: Frontend ↔ Anthropic API ↔ MCP Server
```

### 4. AI Integration

**Model:** Claude Sonnet 4.5 via Anthropic API

**Why Claude over local LLMs:**
- Superior tool calling reliability (critical for 80+ tool calls per song)
- Better music theory understanding and reasoning
- 200K context window (handles full song structure + skills)
- Faster iteration vs. local inference on consumer hardware
- Cost-effective for prototyping ($0.10-0.50 per song iteration)

**Local LLM limitations:**
- Tool calling less robust (malformed JSON, missed parameters)
- Weaker music theory knowledge
- Smaller context windows (8K-32K vs. 200K)
- Requires high-end GPU for 70B models (40GB+ VRAM)
- Degrades over long conversations

**Integration Flow:**
1. User sends message via frontend chat
2. Frontend forwards to Anthropic API with conversation history
3. API calls MCP tools as needed (Claude decides which tools)
4. MCP server executes operations, updates state
5. Frontend receives Claude's response + updated note data
6. Piano roll refreshes to show changes

---

## Context Window & Token Management

### Problem
A dense piece with thousands of notes (as an arbitrary example: 4000 notes) could consume significant context. Need strategy to stay within limits.

### Token Estimates

**Note Representation:**

For a dense piece (as an arbitrary example: 4000 notes):

- **Compact string (for reading notes back):** `"piano,60,0.0,0.5"` ≈ 5 tokens/note
  - 4000 notes × 5 tokens = 20K tokens
- **Structured JSON (for tool calls):** `{"track":"piano","pitch":60,"start":0.0,"dur":0.5}` ≈ 12 tokens/note
  - 4000 notes × 12 tokens = 48K tokens

**Rationale:** MCP tools accept structured JSON for clarity and type safety. When Claude reads notes back for analysis, the server can return compact string format to conserve tokens.

**With Batch Tool Calls:**
- 50 notes per call × 80 calls = 4000 notes
- ~600 tokens per call + ~100 tokens response
- Total: ~56K tokens for full piece (28% of 200K context window)

**Remaining Budget:**
- System prompts + skills: ~10K tokens
- Conversation history: ~20K tokens
- **Available for iteration: ~114K tokens**

### Optimization Strategies

#### 1. Section-Based Organization
```python
# Structure song into sections
add_section("intro", 1, 4, "Sparse piano, building tension")
add_section("verse1", 5, 12, "Full arrangement, C minor")
add_section("chorus1", 13, 20, "Key change to Eb, maximal density")
```

**Benefits:**
- Work on sections independently (~250 notes each vs. 4000 total)
- Only load relevant notes: `get_notes("all", measures=[5,12])` ≈ 3K tokens
- Reduce context consumption by 90% when iterating

#### 2. Section Descriptions
```python
add_section("verse1", 5, 12, 72, "4/4", "Dm",
            "Dm9-G7alt-Cmaj9 progression, rootless voicings,
             strings double melody at octave for richness")
```

**Benefits:**
- High-level understanding without reparsing note data (~50 tokens vs. 3000)
- Enables style transfer: "Apply verse1 harmony approach to verse2"
- Supports debugging: "Why did you use that chord?" → Check section description
- Human-readable compositional reasoning

#### 3. Selective Note Reading
```python
# Instead of loading all 4000 notes
get_notes("all", measures=[1, 32])  # 48K tokens

# Load only what's needed
get_piece_info()                  # Sections overview: ~500 tokens
get_notes("piano", measures=[5,8]) # Specific section: ~1K tokens
```

**Iteration Cost Per Section:**
- Read section notes: ~3K tokens
- Update section description: ~50 tokens
- Rewrite section: ~3.6K tokens
- **Total: ~6.7K tokens** (vs. 56K for full song)

---

## Compositional Workflow

### Phase 1: Planning (High-Level)
```
User: "Write a melancholic jazz ballad for piano and strings"

Claude reasoning:
1. Analyze request: melancholic → minor key, slower tempo, descending motifs
2. Jazz ballad → extended harmony, rubato feel
3. Plan structure: intro (4 bars) → verse (8 bars) → chorus (8 bars) → outro (4 bars)
4. Choose key: D minor (comfortable range, not too dark)

Tool calls:
- set_title("Melancholic Jazz Ballad")
- add_section("intro", 1, 4, 72, "4/4", "Dm", "Sparse piano, melancholic mood setting")
- add_section("verse", 5, 12, 72, "4/4", "Dm", "Piano + strings, main theme")
- add_track("piano", "acoustic grand piano")
- add_track("strings", "string ensemble")
```

### Phase 2: Execution (Section-by-Section)
```
Claude reasoning for intro:
1. Read intro section details
2. Apply jazz ballad skills: rootless voicings, extended chords
3. Apply melancholic principles: descending melody, slower harmonic rhythm
4. Decide: Start with Dm9, descend to A7alt
5. Piano left hand: bass + chord foundation (rootless)
6. Piano right hand: melody D5→A4 with chromatic passing

Tool calls:
- add_notes([
    {"track": "piano", "pitch": 38, "start": 0, "duration": 2},  # D2 bass
    {"track": "piano", "pitch": 53, "start": 0, "duration": 2},  # F3
    {"track": "piano", "pitch": 60, "start": 0, "duration": 2},  # C4
    {"track": "piano", "pitch": 62, "start": 0, "duration": 2},  # D4 (9th)
    {"track": "piano", "pitch": 74, "start": 0, "duration": "1/2"},  # D5 melody
    # ... more notes
  ])
```

**Note:** The section's description field documents the musical decisions: "Sparse piano, melancholic mood setting. Dm9-G7alt-Cmaj7-A7alt, descending melody D→A, rootless voicings for open jazz sound."

### Phase 3: Iteration (Refinement)
```
User: "The intro feels too dense"

Claude reasoning:
1. Read intro section and notes
2. Identify issue: 5-note voicings too thick
3. Solution: Simplify to 3-note voicings, more space between notes

Tool calls:
- remove_notes_in_range("piano", 0.0, 16.0)  # 4 measures in 4/4 = 16 beats
- add_notes([simplified voicings])
- edit_section("intro", description="Sparse piano, melancholic. Revised to 3-note voicings,
               added rhythmic space. Dm9-G7alt-Cmaj7-A7alt progression.")
```

---

## Design Rationale & Tradeoffs

### Why This Approach

**Advantages over tokenized generation:**
1. **Explainability:** Every decision captured in journal, traceable reasoning
2. **Editability:** Surgical changes to specific sections without regenerating entire piece
3. **Control:** Explicit musical constraints easier to enforce (e.g., "stay in C major pentatonic")
4. **Iteration:** User feedback loops more natural ("make verse darker" → specific edits)
5. **Debugging:** Can introspect and fix mistakes ("why is there a wrong note?" → find and correct)

**Potential advantages in quality:**
- Explicit music theory reasoning vs. hoping transformer learned patterns
- Structured planning (macro → micro) vs. token-by-token generation
- Theory-guided constraints (voice leading, range limits) enforced reliably

### Limitations & Challenges

**1. Speed:**
- Tokenized models: seconds for full piece
- This approach: minutes for complex arrangements (80+ sequential tool calls)
- **Mitigation:** Acceptable for prototype; batch operations help; user watches composition unfold

**2. Musical Flow:**
- Tokenized models learn implicit patterns from training data
- This approach relies on explicit skills + LLM reasoning
- **Risk:** May lack "gestalt" intuition that comes from seeing millions of examples
- **Mitigation:** Comprehensive skills, iterative refinement, hybrid approach possible

**3. Context Consumption:**
- Hundreds of tool calls + responses for full piece
- **Mitigation:** Section-based organization, selective reading, journal summaries

**4. LLM Limitations:**
- Even Claude may make musical mistakes
- Tool calling reliability critical (any malformed call breaks workflow)
- **Mitigation:** Clear tool schemas, comprehensive skills, undo/redo functionality

### Comparison to Alternatives

| Aspect | Tokenized (MIDI-LLM) | This Approach | Local LLM + Tools |
|--------|---------------------|---------------|-------------------|
| **Generation Speed** | Fast (~10s for 2K tokens) | Slower (minutes) | Very slow |
| **Musical Quality** | Mixed (benchmarks ≠ human ears) | TBD (hypothesis: better with reasoning) | Likely poor |
| **Explainability** | Opaque | High (journal + reasoning) | Medium |
| **Editability** | Difficult | Easy (surgical edits) | Difficult (context issues) |
| **Control** | Limited | High | Low |
| **Cost** | Training: expensive, Inference: cheap | API: ~$0.50/song | Hardware: upfront cost |
| **Tool Calling** | N/A | Reliable (Claude) | Unreliable |

---

## Implementation Plan

### Phase 1: MCP Server + Claude Desktop (1-2 days)
**Goal:** Validate that Claude + skills can compose coherently

**Tasks:**
1. Scaffold MCP server with Python + mcp SDK
2. Implement basic tools: `set_title`, `add_section`, `add_track`, `add_notes`, `get_notes`
3. Create initial skills: basic harmony, melody principles
4. Configure Claude Desktop to use MCP server
5. Test: "Write a simple 8-bar melody with basic harmony"
6. Manually export MIDI, listen in external DAW (Logic, Ableton, MuseScore)

**Success Criteria:**
- Tool calls execute without errors
- Generated MIDI sounds musically coherent
- Section descriptions show reasonable compositional reasoning

### Phase 2: Complete MCP Tools + Core Skills (3-5 days)
**Goal:** Full CRUD operations and comprehensive music theory knowledge

**Tasks:**
1. Implement remaining tools: edit_section, remove_notes, undo/redo, export_midi
2. Add batch operations: `add_notes` accepts arrays with expression support
3. Build skills library:
   - Core theory: intervals, chords, voice leading, progressions
   - Genres: Baroque, Classical, Romantic, Jazz
   - Instrumentation: piano, strings, brass, winds, drums
4. Test complex compositions: multi-track, multiple sections, 1000+ notes
5. Verify context window management with section-based reading

**Success Criteria:**
- Can compose 4000-note piece within context limits
- Section descriptions enable understanding of compositional decisions
- Skills guide Claude to genre-appropriate, musically sensible outputs

### Phase 3: Minimal Frontend (3-5 days)
**Goal:** Basic GUI without leaving prototype app

**Tasks:**
1. Set up Electron + React project
2. Implement chat panel (send to Anthropic API, display responses)
3. Display track list and note data (simple list view, not piano roll yet)
4. Add playback with Tone.js (synthesize MIDI in browser)
5. Wire MCP server to frontend via bridge
6. Add export button (save MIDI file)

**Success Criteria:**
- End-to-end workflow: chat → Claude generates → frontend updates → playback works
- No need to switch to external DAW for basic testing

### Phase 4: Piano Roll + Manual Editing (1-2 weeks)
**Goal:** Visual editing and human-AI collaboration

**Tasks:**
1. Integrate piano roll component (react-piano-component or custom Canvas)
2. Sync piano roll with MCP state (notes → visualization)
3. Implement manual editing: add/remove/move notes with mouse
4. Add quantization options (snap to grid)
5. Handle bidirectional updates: manual edits → MCP state → Claude can read changes
6. Improve UX: track colors, note selection, copy/paste

**Success Criteria:**
- User can manually edit Claude's output
- Claude can "see" and work with user's manual edits
- Piano roll feels responsive (no lag)

### Phase 5: Iteration & Refinement (Ongoing)
**Tasks:**
- Gather user feedback on compositional quality
- Expand skills based on observed gaps or mistakes
- Optimize context window usage if hitting limits
- Add undo history visualization
- Improve section description searchability and editing

---

## Technology Stack

### MCP Server
- **Language:** Python 3.10+
- **Framework:** `mcp` (Anthropic SDK)
- **MIDI:** `mido` (simple, Pythonic)
- **Data:** In-memory dict/list, JSON serialization for persistence

### Frontend DAW
- **Platform:** Electron (cross-platform desktop)
- **UI Framework:** React or Svelte
- **Piano Roll:** `react-piano-component` or custom Canvas/WebGL
- **Audio:** Tone.js (browser-based synthesis, no system MIDI needed)
- **API Client:** `@anthropic-ai/sdk` (JavaScript)

### AI
- **Model:** Claude Sonnet 4.5 via Anthropic API
- **Cost:** ~$3/M input tokens, ~$15/M output tokens
- **Budget:** $50-100 for prototyping (100-200 song iterations)

### Skills
- **Format:** Markdown files in `/mnt/skills/user/`
- **Version Control:** Git (track skill evolution)

---

## Cost & Performance Estimates

### Token Usage (4000-note piece)
- Full piece generation: ~56K tokens output ($0.84)
- Typical iteration: ~7K tokens per section ($0.10)
- Average composition session: 5-10 iterations = $0.50-1.00
- Prototype budget: $50-100 = 50-200 compositions

### Generation Time
- Planning phase: ~10 seconds (structure + section setup)
- Section generation (250 notes): ~30 seconds (batch tool calls)
- Full 4000-note piece: ~5-8 minutes (16 sections)
- Iteration on section: ~1 minute

### Context Window Usage
- Skills: ~10K tokens (loaded once per session)
- System prompts: ~5K tokens
- Song structure + section descriptions: ~2K tokens
- Active section notes: ~3K tokens
- Conversation history: ~20K tokens
- **Total active context: ~40K tokens (20% of 200K limit)**
- **Remaining for iteration: ~160K tokens**

---

## Success Metrics

### Objective
- ✅ Generate 4000-note piece without context overflow
- ✅ Complete composition in <10 minutes
- ✅ Execute 80+ tool calls without errors
- ✅ Export valid MIDI file playable in standard DAWs

### Subjective (Human Evaluation)
- Does the music sound coherent and musical?
- Can users understand compositional decisions via section descriptions?
- Is iteration workflow intuitive and effective?
- Does manual editing + AI generation feel collaborative?

### Comparison Baseline
- Listen to MIDI-LLM and Text2Midi outputs on same prompts
- Evaluate if this approach achieves better musical quality
- If not clearly better, reconsider or pivot to hybrid approach

---

## Risk Assessment

### High Risk
1. **Musical quality doesn't exceed tokenized models**
   - Mitigation: Iterative skill refinement, hybrid approach (tokenized initial draft + tool-based editing)
   
2. **Context window overflow on complex pieces**
   - Mitigation: Section-based reading tested in Phase 2, optimize before building frontend

### Medium Risk
3. **Tool calling reliability issues**
   - Mitigation: Claude Sonnet 4.5 has strong tool use, clear schemas, comprehensive error handling
   
4. **LLM makes persistent musical mistakes**
   - Mitigation: Undo/redo, manual editing, skill improvements based on observed errors
   - **Note on quantization:** To minimize math errors in note timing, Claude can output arithmetic expressions rather than computed floats (e.g., `start = "1.5 * 12.33"` for "second triplet note in bar 12"). This trades slightly higher token usage for more reliable quantization. The MCP server can evaluate these expressions.

### Low Risk
5. **Frontend complexity**
   - Mitigation: Use existing libraries (react-piano-component, Tone.js), MVP features only
   
6. **Cost overruns**
   - Mitigation: $50-100 budget sufficient for 50-200 iterations, reasonable for prototype

---

## Alternative Approaches Considered

### 1. High-Level MCP Tools (e.g., `harmonize_melody()`)
**Rejected because:** MCP tools should be deterministic. "Harmonize" involves creative decisions that should live in the LLM, not hidden in tool logic. Makes reasoning opaque.

### 2. Local LLMs (Llama 3.1 70B, etc.)
**Rejected because:** Tool calling less reliable, weaker music theory understanding, requires expensive GPU. API cost ($50-100) cheaper than GPU purchase for prototyping.

### 3. Hybrid: Tokenized Generation + Tool-Based Editing
**Future consideration:** Use MIDI-LLM for fast initial draft, then this approach for refinement. Could combine speed advantage of tokenized with control/explainability of tools. Worthwhile if pure tool-based approach doesn't achieve satisfactory quality.

### 4. Training Custom Model on Tool-Based Reasoning
**Future consideration:** If approach succeeds, could fine-tune models to improve tool-based composition. Would need dataset of high-quality tool-based composition traces.

---

## Open Questions

1. Will explicit music theory reasoning produce more musical outputs than learned implicit patterns?
2. Can LLMs maintain stylistic coherence across 80+ tool calls without "forgetting" earlier decisions?
3. What's the minimum skill documentation needed for acceptable quality?
4. Should section descriptions be user-editable in the UI (e.g., user corrects Claude's musical analysis)?
5. How to handle complex orchestration decisions spanning multiple tracks simultaneously?

---

## Conclusion

This design proposes an alternative to end-to-end tokenized MIDI generation by separating creative reasoning (LLM + skills) from deterministic operations (MCP tools). The approach prioritizes explainability, editability, and control, with the hypothesis that explicit music theory reasoning may produce more musically coherent outputs than learned implicit patterns.

Key innovations:
- **Section descriptions** for transparent decision-making
- **Section-based organization** for context efficiency
- **Low-level CRUD tools** to keep creativity in the LLM
- **Comprehensive skills** teaching principles over formulas
- **Expression support** for note timing (e.g., "9 + 1/3") to minimize quantization errors

Success depends on whether LLM reasoning + music theory knowledge can match or exceed the musical quality of models trained on millions of examples. The prototype will test this hypothesis with manageable risk and cost.
