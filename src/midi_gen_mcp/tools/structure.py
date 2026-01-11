"""Structure/section management tools."""

from typing import Optional
from midi_gen_mcp.state import get_state, before_mutation


def add_section(
    name: str,
    start_measure: int,
    end_measure: int,
    tempo: int,
    time_signature: str,
    key: str,
    description: str = ""
) -> str:
    """
    Add a new section to the piece.

    Args:
        name: Section name (must be unique)
        start_measure: Starting measure (1-indexed)
        end_measure: Ending measure (inclusive)
        tempo: Tempo in BPM
        time_signature: Time signature (e.g., "4/4", "6/8")
        key: Key signature (e.g., "C", "Am", "F#m")
        description: Optional description/journal

    Returns:
        Confirmation message
    """
    before_mutation()
    state = get_state()

    # Check for duplicate name
    if any(s["name"] == name for s in state.sections):
        return f"Error: Section '{name}' already exists"

    # Validate measures
    if start_measure < 1:
        return "Error: start_measure must be >= 1"
    if end_measure < start_measure:
        return "Error: end_measure must be >= start_measure"

    section = {
        "name": name,
        "start_measure": start_measure,
        "end_measure": end_measure,
        "tempo": tempo,
        "time_signature": time_signature,
        "key": key,
        "description": description
    }

    state.sections.append(section)

    # Keep sections sorted by start_measure
    state.sections.sort(key=lambda s: s["start_measure"])

    return f"Added section '{name}' (measures {start_measure}-{end_measure})"


def edit_section(name: str, **kwargs) -> str:
    """
    Edit an existing section. Automatically adjusts neighboring sections to prevent overlaps.

    Args:
        name: Name of the section to edit
        **kwargs: Fields to update (start_measure, end_measure, tempo, time_signature, key, description)

    Returns:
        Confirmation message

    Note:
        When changing start_measure or end_measure, neighboring sections will be automatically
        trimmed to prevent overlaps.
    """
    before_mutation()
    state = get_state()

    # Find section
    section_idx = None
    for i, s in enumerate(state.sections):
        if s["name"] == name:
            section_idx = i
            break

    if section_idx is None:
        return f"Error: Section '{name}' not found"

    section = state.sections[section_idx]

    # Update fields
    for key, value in kwargs.items():
        if key in section:
            section[key] = value
        else:
            return f"Error: Invalid field '{key}'"

    # Validate measures if changed
    if "start_measure" in kwargs or "end_measure" in kwargs:
        if section["start_measure"] < 1:
            return "Error: start_measure must be >= 1"
        if section["end_measure"] < section["start_measure"]:
            return "Error: end_measure must be >= start_measure"

        # Adjust neighboring sections to prevent overlaps
        _adjust_neighbors(section_idx)

    # Re-sort sections by start_measure
    state.sections.sort(key=lambda s: s["start_measure"])

    return f"Updated section '{name}'"


def _adjust_neighbors(section_idx: int) -> None:
    """
    Adjust neighboring sections to prevent overlaps.

    Args:
        section_idx: Index of the section that was just edited
    """
    state = get_state()
    sections = state.sections
    current = sections[section_idx]

    # Check previous section (if exists)
    if section_idx > 0:
        prev_section = sections[section_idx - 1]
        # If current section's start overlaps with previous section
        if current["start_measure"] <= prev_section["end_measure"]:
            # Trim previous section to end before current section starts
            prev_section["end_measure"] = current["start_measure"] - 1
            # If this makes previous section invalid, remove it
            if prev_section["end_measure"] < prev_section["start_measure"]:
                sections.pop(section_idx - 1)
                # Adjust index since we removed previous section
                return

    # Check next section (if exists)
    if section_idx < len(sections) - 1:
        next_section = sections[section_idx + 1]
        # If current section's end overlaps with next section
        if current["end_measure"] >= next_section["start_measure"]:
            # Trim next section to start after current section ends
            next_section["start_measure"] = current["end_measure"] + 1
            # If this makes next section invalid, remove it
            if next_section["start_measure"] > next_section["end_measure"]:
                sections.pop(section_idx + 1)


def get_sections() -> list[dict]:
    """
    Get all sections in the piece.

    Returns:
        List of section dictionaries, sorted by start_measure
    """
    state = get_state()
    return state.sections.copy()
