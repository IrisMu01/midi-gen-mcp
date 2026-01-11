"""MIDI file export functionality."""

from typing import Union, List, Dict, Any
import mido
from midi_gen_mcp.state import get_state


# Constants
TICKS_PER_BEAT = 480  # Standard MIDI resolution (quarter note = 480 ticks)
DEFAULT_VELOCITY = 64  # Medium velocity (0-127)


# General MIDI Instrument Mapping (Program Numbers 0-127)
# https://www.midi.org/specifications-old/item/gm-level-1-sound-set
GM_INSTRUMENTS = {
    # Piano (0-7)
    "piano": 0,
    "acoustic_grand_piano": 0,
    "bright_acoustic_piano": 1,
    "electric_grand_piano": 2,
    "honky_tonk_piano": 3,
    "electric_piano_1": 4,
    "electric_piano_2": 5,
    "harpsichord": 6,
    "clavinet": 7,

    # Chromatic Percussion (8-15)
    "celesta": 8,
    "glockenspiel": 9,
    "music_box": 10,
    "vibraphone": 11,
    "marimba": 12,
    "xylophone": 13,
    "tubular_bells": 14,
    "dulcimer": 15,

    # Organ (16-23)
    "organ": 16,
    "drawbar_organ": 16,
    "percussive_organ": 17,
    "rock_organ": 18,
    "church_organ": 19,
    "reed_organ": 20,
    "accordion": 21,
    "harmonica": 22,
    "tango_accordion": 23,

    # Guitar (24-31)
    "guitar": 24,
    "acoustic_guitar_nylon": 24,
    "acoustic_guitar_steel": 25,
    "electric_guitar_jazz": 26,
    "electric_guitar_clean": 27,
    "electric_guitar_muted": 28,
    "overdriven_guitar": 29,
    "distortion_guitar": 30,
    "guitar_harmonics": 31,

    # Bass (32-39)
    "bass": 32,
    "acoustic_bass": 32,
    "electric_bass_finger": 33,
    "electric_bass_pick": 34,
    "fretless_bass": 35,
    "slap_bass_1": 36,
    "slap_bass_2": 37,
    "synth_bass_1": 38,
    "synth_bass_2": 39,

    # Strings (40-47)
    "violin": 40,
    "viola": 41,
    "cello": 42,
    "contrabass": 43,
    "tremolo_strings": 44,
    "pizzicato_strings": 45,
    "orchestral_harp": 46,
    "harp": 46,
    "timpani": 47,

    # Ensemble (48-55)
    "strings": 48,
    "string_ensemble_1": 48,
    "string_ensemble_2": 49,
    "synth_strings_1": 50,
    "synth_strings_2": 51,
    "choir_aahs": 52,
    "choir": 52,
    "voice_oohs": 53,
    "synth_voice": 54,
    "orchestra_hit": 55,

    # Brass (56-63)
    "trumpet": 56,
    "trombone": 57,
    "tuba": 58,
    "muted_trumpet": 59,
    "french_horn": 60,
    "brass_section": 61,
    "brass": 61,
    "synth_brass_1": 62,
    "synth_brass_2": 63,

    # Reed (64-71)
    "saxophone": 64,
    "soprano_sax": 64,
    "alto_sax": 65,
    "tenor_sax": 66,
    "baritone_sax": 67,
    "oboe": 68,
    "english_horn": 69,
    "bassoon": 70,
    "clarinet": 71,

    # Pipe (72-79)
    "piccolo": 72,
    "flute": 73,
    "recorder": 74,
    "pan_flute": 75,
    "blown_bottle": 76,
    "shakuhachi": 77,
    "whistle": 78,
    "ocarina": 79,

    # Synth Lead (80-87)
    "lead": 80,
    "square_lead": 80,
    "sawtooth_lead": 81,
    "calliope_lead": 82,
    "chiff_lead": 83,
    "charang_lead": 84,
    "voice_lead": 85,
    "fifths_lead": 86,
    "bass_lead": 87,

    # Synth Pad (88-95)
    "pad": 88,
    "new_age_pad": 88,
    "warm_pad": 89,
    "polysynth_pad": 90,
    "choir_pad": 91,
    "bowed_pad": 92,
    "metallic_pad": 93,
    "halo_pad": 94,
    "sweep_pad": 95,

    # Synth Effects (96-103)
    "fx_rain": 96,
    "fx_soundtrack": 97,
    "fx_crystal": 98,
    "fx_atmosphere": 99,
    "fx_brightness": 100,
    "fx_goblins": 101,
    "fx_echoes": 102,
    "fx_sci_fi": 103,

    # Ethnic (104-111)
    "sitar": 104,
    "banjo": 105,
    "shamisen": 106,
    "koto": 107,
    "kalimba": 108,
    "bagpipe": 109,
    "fiddle": 110,
    "shanai": 111,

    # Percussive (112-119)
    "tinkle_bell": 112,
    "agogo": 113,
    "steel_drums": 114,
    "woodblock": 115,
    "taiko_drum": 116,
    "melodic_tom": 117,
    "synth_drum": 118,
    "reverse_cymbal": 119,

    # Sound Effects (120-127)
    "guitar_fret_noise": 120,
    "breath_noise": 121,
    "seashore": 122,
    "bird_tweet": 123,
    "telephone_ring": 124,
    "helicopter": 125,
    "applause": 126,
    "gunshot": 127,

    # Drums (special - channel 9/10)
    "drums": 0,  # Will use channel 9 (percussion channel)
}


def _eval_expression(value: Union[str, int, float]) -> float:
    """
    Evaluate a mathematical expression or numeric value to a float.

    Args:
        value: Either a number or a string expression

    Returns:
        The evaluated result as a float
    """
    if isinstance(value, (int, float)):
        return float(value)

    try:
        result = eval(str(value), {"__builtins__": {}}, {})
        return float(result)
    except Exception as e:
        raise ValueError(f"Invalid expression '{value}': {e}")


def _get_instrument_program(instrument: str) -> int:
    """
    Get the General MIDI program number for an instrument.

    Args:
        instrument: Instrument name (case-insensitive)

    Returns:
        GM program number (0-127)
    """
    # Normalize instrument name: lowercase and replace spaces with underscores
    normalized = instrument.lower().replace(" ", "_").replace("-", "_")

    # Look up in GM instruments
    program = GM_INSTRUMENTS.get(normalized)

    if program is None:
        # Default to piano if instrument not found
        return 0

    return program


def _beats_to_ticks(beats: float) -> int:
    """
    Convert beats (quarter notes) to MIDI ticks.

    Args:
        beats: Time in quarter notes

    Returns:
        Time in ticks
    """
    return int(beats * TICKS_PER_BEAT)


def _calculate_section_beat_offset(sections: List[Dict], measure: int, time_signature: str) -> float:
    """
    Calculate the beat offset for a given measure, accounting for varying time signatures.

    Args:
        sections: List of sections with tempo/time signature info
        measure: The measure number (1-indexed)
        time_signature: Time signature string (e.g., "4/4")

    Returns:
        Beat offset (in quarter notes) where this measure starts
    """
    # Parse default time signature
    default_num, default_denom = map(int, time_signature.split("/"))
    beats_per_measure = default_num * (4.0 / default_denom)  # Convert to quarter notes

    # If no sections, use simple calculation
    if not sections:
        return (measure - 1) * beats_per_measure

    # Sort sections by start_measure
    sorted_sections = sorted(sections, key=lambda s: s["start_measure"])

    beat_offset = 0.0
    current_measure = 1

    for section in sorted_sections:
        section_start = section["start_measure"]
        section_ts = section.get("time_signature", time_signature)

        # Parse section time signature
        sec_num, sec_denom = map(int, section_ts.split("/"))
        sec_beats_per_measure = sec_num * (4.0 / sec_denom)

        # If target measure is before this section, use previous time signature
        if measure < section_start:
            beat_offset += (measure - current_measure) * beats_per_measure
            return beat_offset

        # Add beats for measures before this section starts
        if section_start > current_measure:
            beat_offset += (section_start - current_measure) * beats_per_measure
            current_measure = section_start

        # Update beats per measure for this section
        beats_per_measure = sec_beats_per_measure

    # Add remaining measures using last section's time signature
    if measure >= current_measure:
        beat_offset += (measure - current_measure) * beats_per_measure

    return beat_offset


def export_midi(filepath: str) -> str:
    """
    Export the current piece to a MIDI file.

    Args:
        filepath: Path to save the MIDI file (should end in .mid or .midi)

    Returns:
        Confirmation message

    Process:
        1. Evaluate note expressions and convert to absolute ticks
        2. Create note_on/note_off events with absolute tick times
        3. Sort events by tick (note_off after note_on if same tick)
        4. Convert to delta times (relative to previous event)
        5. Write MIDI file with one track per instrument
    """
    state = get_state()

    # Ensure filepath ends with .mid or .midi
    if not (filepath.endswith(".mid") or filepath.endswith(".midi")):
        filepath += ".mid"

    # Create MIDI file (Type 1 = multiple tracks)
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)

    # Group notes by track
    tracks_notes: Dict[str, List[Dict]] = {}
    for note in state.notes:
        track_name = note.get("track")
        if track_name not in tracks_notes:
            tracks_notes[track_name] = []
        tracks_notes[track_name].append(note)

    # Assign MIDI channels to tracks (0-15, with channel 9 reserved for drums)
    track_channels: Dict[str, int] = {}
    channel_idx = 0

    for track_name in sorted(tracks_notes.keys()):
        if track_name not in state.tracks:
            continue

        instrument = state.tracks[track_name].get("instrument", "piano")

        # Check if this is a drum track
        if instrument.lower() in ["drums", "percussion", "drum_kit"]:
            track_channels[track_name] = 9  # Channel 9 (10 in 1-indexed) is percussion
        else:
            # Skip channel 9 for non-drum instruments
            if channel_idx == 9:
                channel_idx += 1
            if channel_idx >= 16:
                channel_idx = 0  # Wrap around if we run out of channels

            track_channels[track_name] = channel_idx
            channel_idx += 1

    # Create a MIDI track for each instrument track
    for track_name in sorted(tracks_notes.keys()):
        if track_name not in state.tracks:
            continue

        instrument = state.tracks[track_name].get("instrument", "piano")
        channel = track_channels[track_name]

        # Create new MIDI track
        midi_track = mido.MidiTrack()
        midi.tracks.append(midi_track)

        # Add track name
        midi_track.append(mido.MetaMessage("track_name", name=track_name, time=0))

        # Set instrument (program change) - unless it's drums
        if channel != 9:
            program = _get_instrument_program(instrument)
            midi_track.append(mido.Message("program_change", program=program, channel=channel, time=0))

        # Set tempo from first section (or default to 120 BPM)
        if state.sections:
            tempo = state.sections[0].get("tempo", 120)
        else:
            tempo = 120

        # Convert BPM to microseconds per beat
        microseconds_per_beat = int(60_000_000 / tempo)
        midi_track.append(mido.MetaMessage("set_tempo", tempo=microseconds_per_beat, time=0))

        # Add time signature from first section (or default to 4/4)
        if state.sections:
            time_sig = state.sections[0].get("time_signature", "4/4")
        else:
            time_sig = "4/4"

        numerator, denominator = map(int, time_sig.split("/"))
        midi_track.append(mido.MetaMessage(
            "time_signature",
            numerator=numerator,
            denominator=denominator,
            clocks_per_click=24,
            notated_32nd_notes_per_beat=8,
            time=0
        ))

        # Create events for all notes in this track
        events = []

        for note in tracks_notes[track_name]:
            pitch = note.get("pitch")
            start_beats = _eval_expression(note.get("start", 0))
            duration_beats = _eval_expression(note.get("duration", 0))

            # Convert to ticks
            start_ticks = _beats_to_ticks(start_beats)
            duration_ticks = _beats_to_ticks(duration_beats)
            end_ticks = start_ticks + duration_ticks

            # Create note_on and note_off events
            events.append({
                "type": "note_on",
                "note": pitch,
                "velocity": DEFAULT_VELOCITY,
                "tick": start_ticks,
                "channel": channel
            })
            events.append({
                "type": "note_off",
                "note": pitch,
                "velocity": 0,
                "tick": end_ticks,
                "channel": channel
            })

        # Sort events by tick, with note_off after note_on if same tick
        events.sort(key=lambda e: (e["tick"], 1 if e["type"] == "note_off" else 0))

        # Convert absolute ticks to delta times
        prev_tick = 0
        for event in events:
            abs_tick = event["tick"]
            delta = abs_tick - prev_tick
            prev_tick = abs_tick

            # Create MIDI message
            if event["type"] == "note_on":
                midi_track.append(mido.Message(
                    "note_on",
                    note=event["note"],
                    velocity=event["velocity"],
                    channel=event["channel"],
                    time=delta
                ))
            elif event["type"] == "note_off":
                midi_track.append(mido.Message(
                    "note_off",
                    note=event["note"],
                    velocity=event["velocity"],
                    channel=event["channel"],
                    time=delta
                ))

        # Add end of track
        midi_track.append(mido.MetaMessage("end_of_track", time=0))

    # Save MIDI file
    midi.save(filepath)

    return f"Exported MIDI to {filepath} ({len(tracks_notes)} tracks, {len(state.notes)} notes)"
