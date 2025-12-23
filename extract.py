#!/usr/bin/env python3
"""Extract Orthodox Study Bible content and load into MongoDB."""
import sys
import warnings
from pathlib import Path

# Suppress XML parsing warnings
warnings.filterwarnings('ignore')

from parser.epub_parser import OSBParser
from parser.mongo_loader import MongoLoader


def main():
    epub_dir = Path("epub_extracted")

    if not epub_dir.exists():
        print(f"Error: {epub_dir} not found. Please extract the EPUB first.")
        sys.exit(1)

    # Parse the EPUB
    print("=" * 60)
    print("ORTHODOX STUDY BIBLE EXTRACTION")
    print("=" * 60)
    print()

    parser = OSBParser(str(epub_dir))
    parser.parse_all()

    # Load into MongoDB
    print("\n" + "=" * 60)
    print("LOADING INTO MONGODB")
    print("=" * 60)

    loader = MongoLoader()
    loader.clear_databases()
    loader.load_all(
        books=parser.books,
        passages=parser.passages,
        annotations=parser.annotations,
        patristic_sources=parser.patristic_sources
    )
    loader.close()

    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)

    # Print summary
    print(f"\nDatabases created:")
    print(f"  ortho_raw - Raw HTML preserved")
    print(f"  ortho_dox - Clean extracted text")
    print(f"\nCollections:")
    print(f"  ortho_dox.books: {len(parser.books)}")
    print(f"  ortho_dox.passages: {len(parser.passages)}")
    print(f"  ortho_dox.annotations: {len(parser.annotations)}")
    print(f"  ortho_dox.patristic_sources: {len(parser.patristic_sources)}")


if __name__ == "__main__":
    main()
