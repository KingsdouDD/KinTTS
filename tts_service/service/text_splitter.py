"""
Text splitter for long-form TTS.
Prioritizes natural language boundaries over character-count hard cuts.
Never rewrites, summarizes, or modifies the input text.
"""

import re


# Primary: sentence-ending punctuation
_PRIMARY_BREAKS = re.compile(r'([。！？；\?!])')
# Secondary: comma/phases that split long sentences
_SECONDARY_BREAKS = re.compile(r'([，、:：])')
# Tertiary: character-level fallback only for extremely long sentences
_CHAR_BREAK = 350


def split_text(text: str, max_chars: int = 300) -> list[str]:
    """
    Split text by natural language boundaries.
    Returns a list of segments, each suitable for one TTS generation call.
    """
    if not text or not text.strip():
        return []

    # First pass: split by primary boundaries
    primary_parts = _PRIMARY_BREAKS.split(text)
    segments = []
    current = ""

    for part in primary_parts:
        # The punctuation character itself appears as its own element after split
        is_punct = part in '。！？；?!' and len(part) == 1
        trial = current + part

        if is_punct:
            # Include the punctuation in current segment
            current = trial
            if len(current) <= max_chars:
                segments.append(current)
                current = ""
            else:
                # Punctuation alone pushed it over - save what we have
                if current:
                    segments.append(current)
                current = part  # start new with just the punctuation
        else:
            if len(trial) <= max_chars:
                current = trial
            else:
                # Would exceed max_chars
                if current:
                    segments.append(current)
                    current = ""
                # Try secondary split on the long part
                sub_parts = _SECONDARY_BREAKS.split(part)
                sub_current = ""
                for sp in sub_parts:
                    is_secondary = sp in '，、:：' and len(sp) == 1
                    sub_trial = sub_current + sp
                    if len(sub_trial) <= max_chars:
                        sub_current = sub_trial
                    else:
                        if sub_current:
                            segments.append(sub_current)
                        sub_current = sp
                current = sub_current

    # Leftover
    if current and current.strip():
        if len(current) <= max_chars:
            segments.append(current)
        else:
            # Fallback: hard cut at max_chars
            chunks = [current[i:i+_CHAR_BREAK] for i in range(0, len(current), _CHAR_BREAK)]
            segments.extend(chunks)

    # Filter empty
    return [s.strip() for s in segments if s.strip()]
