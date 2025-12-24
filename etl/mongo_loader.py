"""MongoDB loader for Orthodox Study Bible data."""
from pymongo import MongoClient
from dataclasses import asdict

from .models import Book, Passage, Annotation, PatristicSource


class MongoLoader:
    """Loads parsed OSB data into MongoDB."""

    def __init__(self, host: str = "localhost", port: int = 27017):
        self.client = MongoClient(host, port)
        self.db_raw = self.client["ortho_raw"]
        self.db_dox = self.client["ortho_dox"]

    def clear_databases(self):
        """Clear existing data."""
        print("Clearing existing databases...")
        self.client.drop_database("ortho_raw")
        self.client.drop_database("ortho_dox")

    def load_all(self, books: dict[str, Book], passages: dict[str, Passage],
                 annotations: dict[str, Annotation], patristic_sources: dict[str, PatristicSource]):
        """Load all data into MongoDB."""
        self._load_books(books)
        self._load_passages(passages)
        self._load_annotations(annotations)
        self._load_patristic_sources(patristic_sources)
        self._create_indexes()

    def _load_books(self, books: dict[str, Book]):
        """Load books into ortho_dox.books."""
        print(f"Loading {len(books)} books...")
        collection = self.db_dox["books"]

        docs = []
        for book in books.values():
            doc = asdict(book)
            doc["_id"] = book.id
            del doc["id"]
            # Add primary abbreviation for backward compatibility
            doc["abbreviation"] = book.abbreviation
            docs.append(doc)

        if docs:
            collection.insert_many(docs)

    def _load_passages(self, passages: dict[str, Passage]):
        """Load passages into both ortho_raw and ortho_dox."""
        print(f"Loading {len(passages)} passages...")

        raw_docs = []
        dox_docs = []

        for passage in passages.values():
            # Raw document - preserve HTML
            raw_doc = {
                "_id": passage.id,
                "book_id": passage.book_id,
                "chapter": passage.chapter,
                "verse": passage.verse,
                "html": passage.html
            }
            raw_docs.append(raw_doc)

            # Clean document
            dox_doc = {
                "_id": passage.id,
                "book_id": passage.book_id,
                "chapter": passage.chapter,
                "verse": passage.verse,
                "text": passage.text,
                "format": passage.format,
                "study_note_ids": passage.study_note_ids,
                "liturgical_ids": passage.liturgical_ids,
                "variant_ids": passage.variant_ids,
                "citation_ids": passage.citation_ids,
                "article_ids": passage.article_ids,
                "cross_ref_targets": passage.cross_ref_targets,
                "cross_ref_text": passage.cross_ref_text,
                "annotation_markers": [
                    {"id": m.id, "type": m.type, "preceding": m.preceding}
                    for m in passage.annotation_markers
                ]
            }
            dox_docs.append(dox_doc)

        if raw_docs:
            self.db_raw["passages"].insert_many(raw_docs)
        if dox_docs:
            self.db_dox["passages"].insert_many(dox_docs)

    def _load_annotations(self, annotations: dict[str, Annotation]):
        """Load annotations into both ortho_raw and ortho_dox."""
        print(f"Loading {len(annotations)} annotations...")

        raw_docs = []
        dox_docs = []

        for ann in annotations.values():
            # Raw document
            raw_doc = {
                "_id": ann.id,
                "type": ann.type,
                "passage_ids": ann.passage_ids,
                "html": ann.html
            }
            raw_docs.append(raw_doc)

            # Clean document
            dox_doc = {
                "_id": ann.id,
                "type": ann.type,
                "passage_ids": ann.passage_ids,
                "verse_display": ann.verse_display,
                "text": ann.text,
                "patristic_citations": ann.patristic_citations,
                "scripture_refs": ann.scripture_refs
            }
            dox_docs.append(dox_doc)

        if raw_docs:
            self.db_raw["annotations"].insert_many(raw_docs)
        if dox_docs:
            self.db_dox["annotations"].insert_many(dox_docs)

    def _load_patristic_sources(self, sources: dict[str, PatristicSource]):
        """Load patristic sources into ortho_dox.patristic_sources."""
        print(f"Loading {len(sources)} patristic sources...")
        collection = self.db_dox["patristic_sources"]

        docs = []
        for source in sources.values():
            doc = {
                "_id": source.id,
                "name": source.name
            }
            docs.append(doc)

        if docs:
            collection.insert_many(docs)

    def _create_indexes(self):
        """Create indexes for efficient querying."""
        print("Creating indexes...")

        # Passages indexes
        self.db_dox["passages"].create_index("book_id")
        self.db_dox["passages"].create_index([("book_id", 1), ("chapter", 1)])
        self.db_dox["passages"].create_index([("book_id", 1), ("chapter", 1), ("verse", 1)])
        self.db_dox["passages"].create_index("cross_ref_targets")
        self.db_dox["passages"].create_index("study_note_ids")
        self.db_dox["passages"].create_index("liturgical_ids")
        self.db_dox["passages"].create_index("variant_ids")
        self.db_dox["passages"].create_index("citation_ids")
        self.db_dox["passages"].create_index("article_ids")
        self.db_dox["passages"].create_index("annotation_markers.id")

        # Annotations indexes
        self.db_dox["annotations"].create_index("type")
        self.db_dox["annotations"].create_index("passage_ids")
        self.db_dox["annotations"].create_index("patristic_citations")

        # Raw passages indexes
        self.db_raw["passages"].create_index("book_id")
        self.db_raw["passages"].create_index([("book_id", 1), ("chapter", 1)])

    def close(self):
        """Close the MongoDB connection."""
        self.client.close()
