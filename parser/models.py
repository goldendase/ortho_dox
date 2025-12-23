"""Data models for Orthodox Study Bible extraction."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnnotationMarker:
    """Position marker for an annotation within a verse."""
    id: str  # e.g., "f4706", "fx283", "fvar1", "fcit1", "fcross24", or article slug
    type: str  # "study", "liturgical", "variant", "citation", "cross_ref", "article"
    preceding: str  # up to 40 chars of text before the marker


@dataclass
class Book:
    """Biblical book metadata."""
    id: str  # e.g., "genesis"
    name: str  # e.g., "Genesis"
    abbreviations: list[str]  # e.g., ["Gen"] or ["Sus", "Dan", "Bel"] for multi-text books
    order: int  # canonical order from manifest
    testament: str  # "old" or "new"
    files: list[str] = field(default_factory=list)  # HTML files for this book

    @property
    def abbreviation(self) -> str:
        """Return primary abbreviation for backward compatibility."""
        return self.abbreviations[0] if self.abbreviations else ""


@dataclass
class Passage:
    """A single verse."""
    id: str  # e.g., "Gen_vchap1-1" - verbatim from epub
    book_id: str  # e.g., "genesis"
    chapter: int
    verse: int
    text: str  # clean extracted text
    html: str  # raw HTML
    format: str  # "prose" or "poetry"
    study_note_ids: list[str] = field(default_factory=list)
    liturgical_ids: list[str] = field(default_factory=list)
    variant_ids: list[str] = field(default_factory=list)
    citation_ids: list[str] = field(default_factory=list)
    article_ids: list[str] = field(default_factory=list)  # Topical study articles
    cross_ref_targets: list[str] = field(default_factory=list)
    cross_ref_text: Optional[str] = None
    annotation_markers: list[AnnotationMarker] = field(default_factory=list)  # Position data for all markers


@dataclass
class Annotation:
    """Study note, liturgical reference, variant, citation, or topical article."""
    id: str  # e.g., "f1", "fx1", "fvar1", "fcit1", or article slug like "creation"
    type: str  # "study", "liturgical", "variant", "citation", or "article"
    passage_ids: list[str]  # verses this annotation applies to
    verse_display: str  # e.g., "1:1" or "1:1-3"
    text: str  # clean text
    html: str  # raw HTML
    patristic_citations: list[str] = field(default_factory=list)
    scripture_refs: list[str] = field(default_factory=list)


@dataclass
class PatristicSource:
    """Church Father or liturgical source."""
    id: str  # abbreviation, e.g., "BasilG"
    name: str  # full name, e.g., "Basil the Great"
