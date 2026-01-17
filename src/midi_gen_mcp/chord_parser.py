"""Chord parsing module using pychord library."""

from typing import List
from pychord import Chord
from pychord.quality import QualityManager


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
    try:
        chord = Chord(symbol)
        # Get the components (pitch classes) of the chord
        chord_tones = [str(component) for component in chord.components()]

        return {
            "chord": symbol,
            "chord_tones": chord_tones
        }
    except Exception as e:
        # Provide helpful error message with supported qualities
        supported = get_supported_qualities()
        raise ValueError(
            f"Invalid chord symbol '{symbol}'. "
            f"Supported qualities: {', '.join(supported)}. "
            f"Examples: C, Cm, C7, Cmaj7, Cdim, Caug, Csus4, C9, C13"
        ) from e


def get_supported_qualities() -> List[str]:
    """Return list of supported chord qualities from pychord."""
    # Get all chord qualities from pychord's QualityManager
    quality_manager = QualityManager()
    return list(quality_manager.get_qualities().keys())
