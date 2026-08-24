"""Hindi-aware preprocessing for the BM25 sparse encoder (Stage 5).

FastEmbed's Qdrant/bm25 (0.8.0) ships stemmers/stopword lists for 18
languages with no Indic option beyond Tamil — so Devanagari text is indexed
raw: function words (का / की / है / …) pollute the sparse index at the same
weight as content words, and morphological variants (राजस्व vs राजस्वीय)
never match between query and passage.

This layer normalizes Devanagari tokens BEFORE encoding: stopword removal
plus ONE light suffix strip (longest-match, minimum stem length). It is
applied symmetrically — queries and passages both go through
`bm25.text_to_sparse`, which is the only property that matters for sparse
matching. Latin/digit tokens pass through untouched, so mixed-script
documents keep their English signal intact.

Gated by BM25_HINDI_ENABLED (default OFF): flipping it changes what gets
indexed, so it must only be enabled together with a full re-ingest —
otherwise preprocessed queries hit unprocessed passages.
"""

from __future__ import annotations

import re

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_SPLIT_RE = re.compile(r"\s+")

# Common Hindi function words (inflected forms included where frequent).
# Deliberately short — false-positive removal of a content word costs more
# than letting a rare stopword through.
_STOPWORDS = frozenset({
    "का", "के", "की", "को", "कि", "किसे", "किन", "ने", "ना", "नहीं",
    "और", "या", "यह", "ये", "इस", "इसे", "इन", "उस", "उसे", "उन",
    "वह", "वे", "है", "हैं", "हो", "हूँ", "हूं", "था", "थी", "थे",
    "थीं", "पर", "परंतु", "द्वारा", "लिए", "बाद", "पहले", "अब", "तब",
    "जब", "तक", "साथ", "भी", "ही", "कोई", "कुछ", "जो", "क्या", "क्यों",
    "कैसे", "कब", "कहाँ", "कहीं", "यहाँ", "वहाँ", "एक", "अत", "इसलिए",
    "उसलिए", "मेरा", "मेरी", "मुझे", "हमें", "हमारा", "तुम्हारा", "आपका",
    "उनका", "सकता", "सकती", "सकते", "रहा", "रही", "रहे", "गया", "गयी",
    "गए", "लिये", "अथवा", "यदि",
})

# Inflection suffixes, longest first; at most ONE strip per token.
_SUFFIXES = (
    "यों", "यें", "ों", "ओं", "ें", "ाकर", "कर", "ीय", "ेर", "ीर",
    "ता", "ती", "ते", "ना", "ने", "नी", "स", "े", "ी", "ा", "ू", "ु", "ि",
)

# Minimum stem length in codepoints (~2 syllables). Blocks over-stemming
# short words like "क्यों" -> "क्य" or "राना" -> "रान".
_MIN_STEM_CODEPOINTS = 4


def contains_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI_RE.search(text))


def _stem(token: str) -> str:
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= _MIN_STEM_CODEPOINTS:
            return token[: -len(suffix)]
    return token


def preprocess(text: str) -> str:
    """Drop Hindi stopwords and lightly stem Devanagari tokens.

    Non-Devanagari tokens (Latin, digits) pass through untouched; text with
    no Devanagari at all returns unchanged (fast path for pure-English
    queries and passages).
    """
    if not text or not contains_devanagari(text):
        return text
    kept = []
    for token in _SPLIT_RE.split(text.strip()):
        if not token:
            continue
        if not contains_devanagari(token):
            kept.append(token)
            continue
        if token in _STOPWORDS:
            continue
        kept.append(_stem(token))
    return " ".join(kept)


# ── Pipeline #3: cross-lingual detection ───────────────────────────

# Romanized Hindi content words. Conservative set: content words only,
# no function words ("ka", "ki") which would false-positive on English.
# Missing a word → variant generation still happens (harmless extra
# search); false positive → one unnecessary Flash-Lite call (~300ms).
_ROMANIZED_HINDI_CONTENT_WORDS = frozenset({
    "kanoon", "vidhik", "nyay", "adalat", "samvidhan", "anuched",
    "dhara", "prakaran", "sansad", "mantri", "adhikari", "niyam",
    "prativedan", "rajya", "sarkar", "karmachari", "lokpal",
    "lokayukta", "nyayalaya", "vakil", "mukadama",
    "pashupalan", "krishi", "kisan", "fasal", "sinchai", "gaon",
    "panchayat", "grameen",
    "bijli", "upbhokta",
})

# Fast pre-check regex (avoids set-intersection for short queries)
_ROMANIZED_HINDI_RE = re.compile(
    r"\b(?:kanoon|vidhik|nyay|samvidhan|anuched|dhara|prakaran|"
    r"sansad|mantri|adhikari|niyam|pashupalan|krishi|kisan|fasal|"
    r"panchayat|grameen|bijli|upbhokta|lokpal|nyayalaya|mukadama|"
    r"sinchai)\b",
    re.IGNORECASE,
)


def is_romanized_hindi(text: str) -> bool:
    """True if Latin-script text contains romanized Hindi content words."""
    return bool(_ROMANIZED_HINDI_RE.search(text))


def needs_cross_lingual_boost(
    query: str,
    has_devanagari_corpus: bool,
) -> bool:
    """Gate: should we generate Hindi variant(s) for this query?

    Decision tree:
      1. No Devanagari docs in corpus  → False  (pure-English tenant)
      2. Query already has Devanagari  → False  (already Hindi-compatible)
      3. Latin script + Devanagari doc → True   (cross-lingual search)

    Case 3 fires for ALL Latin queries (English, romanized Hindi, Hinglish)
    because we cannot distinguish intent at query time. The RRF merge
    ensures no degradation: if no Hindi doc is relevant, its RRF score
    stays low and English results rank higher.
    """
    if not has_devanagari_corpus:
        return False
    if contains_devanagari(query):
        return False
    return True


# ── Pipeline #3 revision: dictionary-first transliteration ──────────

ROMANIZED_TO_DEVANAGARI: dict[str, str] = {
    "kanoon": "कानून", "vidhik": "विधिक", "nyay": "न्याय",
    "adalat": "अदालत", "samvidhan": "संविधान", "anuched": "अनुच्छेद",
    "dhara": "धारा", "prakaran": "प्रकरण", "sansad": "संसद",
    "mantri": "मंत्री", "adhikari": "अधिकारी", "niyam": "नियम",
    "prativedan": "प्रतिवेदन", "rajya": "राज्य", "sarkar": "सरकार",
    "karmachari": "कर्मचारी", "lokpal": "लोकपाल",
    "lokayukta": "लोकायुक्त", "nyayalaya": "न्यायालय",
    "vakil": "वकील", "mukadama": "मुकदमा",
    "pashupalan": "पशुपालन", "krishi": "कृषि", "kisan": "किसान",
    "fasal": "फसल", "sinchai": "सिंचाई", "gaon": "गाँव",
    "panchayat": "पंचायत", "grameen": "ग्रामीण",
    "bijli": "बिजली", "upbhokta": "उपभोकta",
}


def transliterate_romanized_hindi(text: str) -> str:
    """Transliterate romanized Hindi tokens to Devanagari.

    Dictionary-first for known legal/content words (deterministic),
    fallback to indic-transliteration library for unknown tokens.
    English tokens pass through untouched.
    """
    try:
        from indic_transliteration import sanscript as _sanscript

        def _fallback(token: str) -> str:
            return _sanscript.transliterate(token, _sanscript.HK, _sanscript.DEVANAGARI)

    except ImportError:

        def _fallback(token: str) -> str:
            return token

    tokens = re.split(r"(\s+)", text.strip())
    out: list[str] = []
    for tok in tokens:
        if not tok.strip():
            out.append(tok)
            continue
        lower = tok.lower()
        if lower in ROMANIZED_TO_DEVANAGARI:
            out.append(ROMANIZED_TO_DEVANAGARI[lower])
        elif is_romanized_hindi(tok):
            out.append(_fallback(tok))
        else:
            out.append(tok)
    return "".join(out)
