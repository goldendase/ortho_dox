"""Library query service for theological works."""

from api.db import MongoDB
from api.models.library import (
    AuthorDetail,
    AuthorListResponse,
    AuthorRole,
    AuthorSummary,
    AuthorWithCount,
    AuthorWorksResponse,
    ComponentsGroup,
    ComponentType,
    FootnoteComponent,
    ImageComponent,
    LibraryContextResponse,
    LibraryExpandMode,
    LibraryRef,
    LibraryRefAuthor,
    NodeFull,
    NodeMinimal,
    NodeNavigation,
    NodeSummary,
    NodeTOC,
    NodeWithComponents,
    PassageLibraryRefsResponse,
    QuoteComponent,
    ScriptureRefDetail,
    ScriptureRefsResponse,
    ScriptureRefTarget,
    WorkCategory,
    WorkDetail,
    WorkListResponse,
    WorkSummary,
    WorkTOCResponse,
)


# --- Works ---


async def get_works(
    category: WorkCategory | None = None,
    author_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> WorkListResponse:
    """Get all works with optional filtering."""
    db = MongoDB.db_dox

    # Build query filter
    query = {}
    if category:
        query["category"] = category.value
    if author_id:
        query["authors.id"] = author_id

    # Get works
    works_cursor = db.library_works.find(query).skip(offset).limit(limit)
    works_raw = await works_cursor.to_list(length=limit)

    # Get total count
    total = await db.library_works.count_documents(query)

    # Get node counts per work
    node_stats = await db.library_nodes.aggregate([
        {"$group": {
            "_id": "$book_id",
            "node_count": {"$sum": 1},
        }},
    ]).to_list(length=None)
    stats_by_work = {s["_id"]: s for s in node_stats}

    # Check for images
    image_works = await db.library_components.aggregate([
        {"$match": {"component_type": "image"}},
        {"$group": {"_id": "$book_id"}},
    ]).to_list(length=None)
    works_with_images = {w["_id"] for w in image_works}

    works = []
    for work in works_raw:
        work_id = work.get("id", work["_id"])  # Support both id and _id for works
        stats = stats_by_work.get(work_id, {})
        works.append(WorkSummary(
            id=work_id,
            title=work.get("title", ""),
            subtitle=work.get("subtitle"),
            authors=[
                AuthorSummary(
                    id=a.get("id", ""),
                    name=a.get("name", ""),
                    role=AuthorRole(a.get("role", "author")),
                )
                for a in work.get("authors", [])
            ],
            category=WorkCategory(work.get("category", "theological")),
            subjects=work.get("subjects", []),
            node_count=stats.get("node_count", 0),
            has_images=work_id in works_with_images,
        ))

    return WorkListResponse(
        works=works,
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_work(work_id: str) -> WorkDetail | None:
    """Get a single work with full details."""
    db = MongoDB.db_dox

    # Try id field first, fall back to _id
    work = await db.library_works.find_one({"id": work_id})
    if not work:
        work = await db.library_works.find_one({"_id": work_id})
    if not work:
        return None

    # Get node counts
    node_count = await db.library_nodes.count_documents({"book_id": work_id})
    leaf_count = await db.library_nodes.count_documents({"book_id": work_id, "is_leaf": True})

    # Get scripture ref count
    ref_count = await db.library_scripture_refs.count_documents({"book_id": work_id})

    return WorkDetail(
        id=work.get("id", work["_id"]),
        title=work.get("title", ""),
        subtitle=work.get("subtitle"),
        authors=[
            AuthorDetail(
                id=a.get("id", ""),
                name=a.get("name", ""),
                role=AuthorRole(a.get("role", "author")),
                dates=a.get("dates"),
                description=a.get("description"),
            )
            for a in work.get("authors", [])
        ],
        publisher=work.get("publisher"),
        publication_date=work.get("publication_date"),
        isbn=work.get("isbn"),
        category=WorkCategory(work.get("category", "theological")),
        subjects=work.get("subjects", []),
        source_format=work.get("source_format"),
        node_count=node_count,
        leaf_count=leaf_count,
        scripture_ref_count=ref_count,
    )


async def get_work_toc(work_id: str) -> WorkTOCResponse | None:
    """Get work table of contents (tree without content)."""
    db = MongoDB.db_dox

    # Verify work exists - try id field first, fall back to _id
    work = await db.library_works.find_one({"id": work_id}, {"id": 1})
    if not work:
        work = await db.library_works.find_one({"_id": work_id}, {"_id": 1})
    if not work:
        return None

    # Get all nodes for this work
    nodes_cursor = db.library_nodes.find(
        {"book_id": work_id},
        {"id": 1, "parent_id": 1, "title": 1, "label": 1, "node_type": 1, "is_leaf": 1, "order": 1}
    )
    nodes_raw = await nodes_cursor.to_list(length=None)

    if not nodes_raw:
        return None

    # Build tree structure
    nodes_by_id = {n["id"]: n for n in nodes_raw}
    children_by_parent: dict[str | None, list] = {}

    for node in nodes_raw:
        parent_id = node.get("parent_id")
        if parent_id not in children_by_parent:
            children_by_parent[parent_id] = []
        children_by_parent[parent_id].append(node)

    # Sort children by order
    for children in children_by_parent.values():
        children.sort(key=lambda n: n.get("order", 0))

    def build_toc_node(node_data: dict) -> NodeTOC:
        node_id = node_data["id"]
        children = children_by_parent.get(node_id, [])
        return NodeTOC(
            id=node_id,
            title=node_data.get("title"),
            label=node_data.get("label"),
            node_type=node_data.get("node_type", "section"),
            is_leaf=node_data.get("is_leaf", False),
            order=node_data.get("order", 0),
            children=[build_toc_node(c) for c in children],
        )

    # Find root node (parent_id is None)
    root_nodes = children_by_parent.get(None, [])
    if not root_nodes:
        # Try to find the book node
        for node in nodes_raw:
            if node.get("node_type") == "book":
                root_nodes = [node]
                break

    if not root_nodes:
        return None

    root = build_toc_node(root_nodes[0])

    return WorkTOCResponse(work_id=work_id, root=root)


# --- Nodes ---


async def get_node(
    work_id: str,
    node_id: str,
    expand: LibraryExpandMode = LibraryExpandMode.NONE,
) -> NodeMinimal | NodeWithComponents | NodeFull | None:
    """Get a single node with optional expansion."""
    db = MongoDB.db_dox

    node = await db.library_nodes.find_one({"id": node_id, "book_id": work_id})
    if not node:
        return None

    # Base fields
    base = NodeMinimal(
        id=node["id"],
        work_id=node.get("book_id", work_id),
        title=node.get("title"),
        label=node.get("label"),
        node_type=node.get("node_type", "section"),
        depth=node.get("depth", 0),
        is_leaf=node.get("is_leaf", False),
        content=node.get("content") if node.get("is_leaf") else None,
    )

    if expand == LibraryExpandMode.NONE:
        return base

    # Get components
    components = await _get_node_components(work_id, node_id)

    # Get navigation
    navigation = await _get_node_navigation(work_id, node_id, node)

    if expand == LibraryExpandMode.COMPONENTS:
        return NodeWithComponents(
            **base.model_dump(),
            components=components,
            navigation=navigation,
        )

    # expand == FULL - try id field first, fall back to _id
    work = await db.library_works.find_one({"id": work_id})
    if not work:
        work = await db.library_works.find_one({"_id": work_id})
    author = None
    if work and work.get("authors"):
        a = work["authors"][0]
        author = AuthorSummary(
            id=a.get("id", ""),
            name=a.get("name", ""),
            role=AuthorRole(a.get("role", "author")),
        )

    # Get scripture refs for this node
    scripture_refs = await _get_scripture_refs_for_node(work_id, node_id)

    return NodeFull(
        **base.model_dump(),
        components=components,
        navigation=navigation,
        work_title=work.get("title") if work else None,
        author=author,
        scripture_refs=scripture_refs,
    )


async def _get_node_components(work_id: str, node_id: str) -> ComponentsGroup:
    """Get resolved components for a node."""
    db = MongoDB.db_dox

    comps_raw = await db.library_components.find(
        {"book_id": work_id, "source_node_id": node_id}
    ).to_list(length=None)

    footnotes = []
    endnotes = []
    images = []
    quotes = []
    epigraphs = []

    for comp in comps_raw:
        comp_type = comp.get("component_type", "")

        if comp_type == "footnote":
            footnotes.append(FootnoteComponent(
                id=comp["id"],
                type=ComponentType.FOOTNOTE,
                marker=comp.get("marker", ""),
                content=comp.get("content", ""),
            ))
        elif comp_type == "endnote":
            endnotes.append(FootnoteComponent(
                id=comp["id"],
                type=ComponentType.ENDNOTE,
                marker=comp.get("marker", ""),
                content=comp.get("content", ""),
            ))
        elif comp_type == "image":
            images.append(ImageComponent(
                id=comp["id"],
                type=ComponentType.IMAGE,
                image_path=comp.get("image_path", ""),
                caption=comp.get("caption"),
                alt_text=comp.get("alt_text"),
            ))
        elif comp_type == "quote":
            quotes.append(QuoteComponent(
                id=comp["id"],
                type=ComponentType.QUOTE,
                content=comp.get("content", ""),
                attribution=comp.get("attribution"),
            ))
        elif comp_type == "epigraph":
            epigraphs.append(QuoteComponent(
                id=comp["id"],
                type=ComponentType.EPIGRAPH,
                content=comp.get("content", ""),
                attribution=comp.get("attribution"),
            ))

    return ComponentsGroup(
        footnotes=footnotes,
        endnotes=endnotes,
        images=images,
        quotes=quotes,
        epigraphs=epigraphs,
    )


async def _get_node_navigation(work_id: str, node_id: str, node: dict) -> NodeNavigation:
    """Get navigation links for a node.

    For leaf nodes, prev/next point to adjacent leaves in reading order,
    traversing the entire tree structure (not just siblings).
    """
    db = MongoDB.db_dox

    parent_id = node.get("parent_id")

    # Get parent
    parent = None
    if parent_id:
        parent_data = await db.library_nodes.find_one(
            {"id": parent_id},
            {"id": 1, "title": 1, "label": 1, "node_type": 1, "is_leaf": 1}
        )
        if parent_data:
            parent = NodeSummary(
                id=parent_data["id"],
                title=parent_data.get("title"),
                label=parent_data.get("label"),
                node_type=parent_data.get("node_type", "section"),
                is_leaf=parent_data.get("is_leaf", False),
            )

    # For leaf nodes, find prev/next leaves across the entire tree
    # by flattening the TOC structure
    prev_node = None
    next_node = None

    if node.get("is_leaf"):
        # Get all nodes for this work to build tree
        all_nodes = await db.library_nodes.find(
            {"book_id": work_id},
            {"id": 1, "parent_id": 1, "title": 1, "label": 1, "node_type": 1, "is_leaf": 1, "order": 1}
        ).to_list(length=None)

        # Build tree and flatten to get leaves in reading order
        leaves = _flatten_to_leaves(all_nodes)

        # Find current node position and get adjacent leaves
        for i, leaf in enumerate(leaves):
            if leaf["id"] == node_id:
                if i > 0:
                    p = leaves[i - 1]
                    prev_node = NodeSummary(
                        id=p["id"],
                        title=p.get("title"),
                        label=p.get("label"),
                        node_type=p.get("node_type", "section"),
                        is_leaf=True,
                    )
                if i < len(leaves) - 1:
                    n = leaves[i + 1]
                    next_node = NodeSummary(
                        id=n["id"],
                        title=n.get("title"),
                        label=n.get("label"),
                        node_type=n.get("node_type", "section"),
                        is_leaf=True,
                    )
                break
    else:
        # For non-leaf nodes, use sibling-based navigation
        siblings = await db.library_nodes.find(
            {"book_id": work_id, "parent_id": parent_id},
            {"id": 1, "title": 1, "label": 1, "node_type": 1, "is_leaf": 1, "order": 1}
        ).sort("order", 1).to_list(length=None)

        for i, sib in enumerate(siblings):
            if sib["id"] == node_id:
                if i > 0:
                    p = siblings[i - 1]
                    prev_node = NodeSummary(
                        id=p["id"],
                        title=p.get("title"),
                        label=p.get("label"),
                        node_type=p.get("node_type", "section"),
                        is_leaf=p.get("is_leaf", False),
                    )
                if i < len(siblings) - 1:
                    n = siblings[i + 1]
                    next_node = NodeSummary(
                        id=n["id"],
                        title=n.get("title"),
                        label=n.get("label"),
                        node_type=n.get("node_type", "section"),
                        is_leaf=n.get("is_leaf", False),
                    )
                break

    return NodeNavigation(prev=prev_node, next=next_node, parent=parent)


def _flatten_to_leaves(nodes: list[dict]) -> list[dict]:
    """Flatten a list of nodes into leaves in reading order.

    Builds the tree structure from flat node list, then traverses
    depth-first to extract leaves in reading order.
    """
    if not nodes:
        return []

    # Build lookup structures
    nodes_by_id = {n["id"]: n for n in nodes}
    children_by_parent: dict[str | None, list[dict]] = {}

    for node in nodes:
        parent_id = node.get("parent_id")
        if parent_id not in children_by_parent:
            children_by_parent[parent_id] = []
        children_by_parent[parent_id].append(node)

    # Sort children by order
    for children in children_by_parent.values():
        children.sort(key=lambda n: n.get("order", 0))

    # Find root nodes (parent_id is None or node_type is "book")
    root_nodes = children_by_parent.get(None, [])
    if not root_nodes:
        for node in nodes:
            if node.get("node_type") == "book":
                root_nodes = [node]
                break

    # Depth-first traversal to collect leaves
    def collect_leaves(node: dict) -> list[dict]:
        if node.get("is_leaf"):
            return [node]
        children = children_by_parent.get(node["id"], [])
        leaves = []
        for child in children:
            leaves.extend(collect_leaves(child))
        return leaves

    all_leaves = []
    for root in root_nodes:
        all_leaves.extend(collect_leaves(root))

    return all_leaves


# --- Authors ---


async def get_authors(role: AuthorRole | None = None) -> AuthorListResponse:
    """Get all authors with work counts."""
    db = MongoDB.db_dox

    # Aggregate authors from works
    pipeline = [
        {"$unwind": "$authors"},
        {"$group": {
            "_id": "$authors.id",
            "name": {"$first": "$authors.name"},
            "dates": {"$first": "$authors.dates"},
            "work_count": {"$sum": 1},
        }},
        {"$sort": {"name": 1}},
    ]

    if role:
        pipeline.insert(1, {"$match": {"authors.role": role.value}})

    authors_raw = await db.library_works.aggregate(pipeline).to_list(length=None)

    authors = [
        AuthorWithCount(
            id=a["_id"],  # _id from aggregation grouping
            name=a.get("name", ""),
            dates=a.get("dates"),
            work_count=a.get("work_count", 0),
        )
        for a in authors_raw
    ]

    return AuthorListResponse(authors=authors, total=len(authors))


async def get_author(author_id: str) -> AuthorDetail | None:
    """Get author details."""
    db = MongoDB.db_dox

    # Find author from any work
    work = await db.library_works.find_one(
        {"authors.id": author_id},
        {"authors.$": 1}
    )

    if not work or not work.get("authors"):
        return None

    a = work["authors"][0]
    return AuthorDetail(
        id=a.get("id", author_id),
        name=a.get("name", ""),
        role=AuthorRole(a.get("role", "author")),
        dates=a.get("dates"),
        description=a.get("description"),
    )


async def get_author_works(author_id: str) -> AuthorWorksResponse | None:
    """Get all works by an author."""
    db = MongoDB.db_dox

    # Get author info
    author = await get_author(author_id)
    if not author:
        return None

    # Get works
    works_raw = await db.library_works.find(
        {"authors.id": author_id}
    ).to_list(length=None)

    # Find the specific role for this author in each work
    works = []
    for work in works_raw:
        author_role = AuthorRole.AUTHOR
        for a in work.get("authors", []):
            if a.get("id") == author_id:
                author_role = AuthorRole(a.get("role", "author"))
                break

        works.append(WorkSummary(
            id=work.get("id", work["_id"]),
            title=work.get("title", ""),
            subtitle=work.get("subtitle"),
            authors=[
                AuthorSummary(
                    id=a.get("id", ""),
                    name=a.get("name", ""),
                    role=AuthorRole(a.get("role", "author")),
                )
                for a in work.get("authors", [])
            ],
            category=WorkCategory(work.get("category", "theological")),
            subjects=work.get("subjects", []),
        ))

    return AuthorWorksResponse(
        author=AuthorSummary(id=author.id, name=author.name, role=author.role),
        works=works,
        total=len(works),
    )


# --- Scripture References ---


async def _get_scripture_refs_for_node(work_id: str, node_id: str) -> list[ScriptureRefTarget]:
    """Get scripture references for a specific node."""
    db = MongoDB.db_dox

    refs_raw = await db.library_scripture_refs.find(
        {"book_id": work_id, "source_node_id": node_id}
    ).to_list(length=None)

    refs = []
    for ref in refs_raw:
        # Get passage preview from OSB
        passage_id = _build_passage_id(ref)
        preview = await _get_passage_preview(passage_id)

        refs.append(ScriptureRefTarget(
            passage_id=passage_id,
            book_id=ref.get("target_book", ""),
            book_name=_get_book_name(ref.get("target_book", "")),
            chapter=ref.get("chapter", 0),
            verse_start=ref.get("verse_start", 0),
            verse_end=ref.get("verse_end"),
            preview=preview,
        ))

    return refs


async def get_work_scripture_refs(
    work_id: str,
    book_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> ScriptureRefsResponse | None:
    """Get all scripture references from a work."""
    db = MongoDB.db_dox

    # Verify work exists - try id field first, fall back to _id
    work = await db.library_works.find_one({"id": work_id}, {"title": 1})
    if not work:
        work = await db.library_works.find_one({"_id": work_id}, {"title": 1})
    if not work:
        return None

    # Build query
    query = {"book_id": work_id}
    if book_filter:
        query["target_book"] = book_filter

    # Get refs with pagination
    refs_raw = await db.library_scripture_refs.find(query).skip(offset).limit(limit).to_list(length=limit)
    total = await db.library_scripture_refs.count_documents(query)

    # Get node titles for context
    node_ids = list({r.get("source_node_id") for r in refs_raw if r.get("source_node_id")})
    nodes = await db.library_nodes.find(
        {"id": {"$in": node_ids}},
        {"id": 1, "title": 1}
    ).to_list(length=None)
    node_titles = {n["id"]: n.get("title") for n in nodes}

    refs = []
    for ref in refs_raw:
        passage_id = _build_passage_id(ref)
        preview = await _get_passage_preview(passage_id)

        refs.append(ScriptureRefDetail(
            id=ref["id"],
            source_node_id=ref.get("source_node_id", ""),
            source_node_title=node_titles.get(ref.get("source_node_id")),
            reference_text=ref.get("reference_text", ""),
            target=ScriptureRefTarget(
                passage_id=passage_id,
                book_id=ref.get("target_book", ""),
                book_name=_get_book_name(ref.get("target_book", "")),
                chapter=ref.get("chapter", 0),
                verse_start=ref.get("verse_start", 0),
                verse_end=ref.get("verse_end"),
                preview=preview,
            ),
        ))

    return ScriptureRefsResponse(
        work_id=work_id,
        work_title=work.get("title"),
        scripture_refs=refs,
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_node_scripture_refs(
    work_id: str,
    node_id: str,
) -> ScriptureRefsResponse | None:
    """Get scripture references from a specific node."""
    db = MongoDB.db_dox

    # Verify node exists
    node = await db.library_nodes.find_one(
        {"id": node_id, "book_id": work_id},
        {"title": 1}
    )
    if not node:
        return None

    # Get work title - try id field first, fall back to _id
    work = await db.library_works.find_one({"id": work_id}, {"title": 1})
    if not work:
        work = await db.library_works.find_one({"_id": work_id}, {"title": 1})

    # Get refs
    refs_raw = await db.library_scripture_refs.find(
        {"book_id": work_id, "source_node_id": node_id}
    ).to_list(length=None)

    refs = []
    for ref in refs_raw:
        passage_id = _build_passage_id(ref)
        preview = await _get_passage_preview(passage_id)

        refs.append(ScriptureRefDetail(
            id=ref["id"],
            source_node_id=node_id,
            source_node_title=node.get("title"),
            reference_text=ref.get("reference_text", ""),
            target=ScriptureRefTarget(
                passage_id=passage_id,
                book_id=ref.get("target_book", ""),
                book_name=_get_book_name(ref.get("target_book", "")),
                chapter=ref.get("chapter", 0),
                verse_start=ref.get("verse_start", 0),
                verse_end=ref.get("verse_end"),
                preview=preview,
            ),
        ))

    return ScriptureRefsResponse(
        work_id=work_id,
        work_title=work.get("title") if work else None,
        scripture_refs=refs,
        total=len(refs),
        limit=len(refs),
        offset=0,
    )


# --- OSB Integration (Reverse Lookup) ---


async def get_library_refs_for_passage(passage_id: str) -> PassageLibraryRefsResponse:
    """Get all library refs that cite a specific OSB passage."""
    db = MongoDB.db_dox

    # Parse passage_id to get book/chapter/verse
    # Format: Gen_vchap1-1 -> genesis, 1, 1
    book_id, chapter, verse = _parse_passage_id(passage_id)

    # Find refs that match this passage
    query = {
        "target_book": book_id,
        "chapter": chapter,
        "verse_start": {"$lte": verse},
        "$or": [
            {"verse_end": {"$gte": verse}},
            {"verse_end": None, "verse_start": verse},
        ],
    }

    refs_raw = await db.library_scripture_refs.find(query).to_list(length=None)

    # Get work and node info for each ref
    work_ids = list({r.get("book_id") for r in refs_raw if r.get("book_id")})
    node_ids = list({r.get("source_node_id") for r in refs_raw if r.get("source_node_id")})

    works = await db.library_works.find(
        {"$or": [{"id": {"$in": work_ids}}, {"_id": {"$in": work_ids}}]},
        {"_id": 1, "id": 1, "title": 1, "authors": 1}
    ).to_list(length=None)
    works_by_id = {w.get("id", w["_id"]): w for w in works}

    nodes = await db.library_nodes.find(
        {"id": {"$in": node_ids}},
        {"id": 1, "title": 1, "content": 1}
    ).to_list(length=None)
    nodes_by_id = {n["id"]: n for n in nodes}

    library_refs = []
    for ref in refs_raw:
        work = works_by_id.get(ref.get("book_id"))
        node = nodes_by_id.get(ref.get("source_node_id"))

        if not work:
            continue

        author = None
        if work.get("authors"):
            a = work["authors"][0]
            author = LibraryRefAuthor(id=a.get("id", ""), name=a.get("name", ""))

        # Get context snippet
        context_snippet = None
        if node and node.get("content"):
            ref_text = ref.get("reference_text", "")
            content = node["content"]
            # Find the reference in content and extract surrounding context
            idx = content.find(ref_text)
            if idx >= 0:
                start = max(0, idx - 50)
                end = min(len(content), idx + len(ref_text) + 50)
                context_snippet = "..." + content[start:end] + "..."

        library_refs.append(LibraryRef(
            work_id=ref.get("book_id", ""),
            work_title=work.get("title", ""),
            node_id=ref.get("source_node_id", ""),
            node_title=node.get("title") if node else None,
            author=author,
            reference_text=ref.get("reference_text", ""),
            context_snippet=context_snippet,
        ))

    # Build display string
    passage_display = _format_passage_display(book_id, chapter, verse)

    return PassageLibraryRefsResponse(
        passage_id=passage_id,
        passage_display=passage_display,
        library_refs=library_refs,
        total=len(library_refs),
    )


# --- Context ---


async def get_library_context(work_id: str, node_id: str) -> LibraryContextResponse | None:
    """Get rich context bundle for MCP consumption."""
    db = MongoDB.db_dox

    # Get node with components
    node = await get_node(work_id, node_id, LibraryExpandMode.COMPONENTS)
    if not node or not isinstance(node, NodeWithComponents):
        return None

    # Get author - try id field first, fall back to _id
    work = await db.library_works.find_one({"id": work_id})
    if not work:
        work = await db.library_works.find_one({"_id": work_id})
    author = None
    if work and work.get("authors"):
        a = work["authors"][0]
        author = AuthorDetail(
            id=a.get("id", ""),
            name=a.get("name", ""),
            role=AuthorRole(a.get("role", "author")),
            dates=a.get("dates"),
            description=a.get("description"),
        )

    # Get scripture refs
    scripture_refs = await _get_scripture_refs_for_node(work_id, node_id)

    return LibraryContextResponse(
        node=node,
        author=author,
        scripture_references=scripture_refs,
        navigation=node.navigation,
    )


# --- Helper Functions ---


def _build_passage_id(ref: dict) -> str:
    """Build OSB passage ID from scripture reference."""
    book_id = ref.get("target_book", "")
    chapter = ref.get("chapter", 0)
    verse = ref.get("verse_start", 0)

    # Map book_id to abbreviation for passage ID
    abbrev = _get_book_abbrev(book_id)
    return f"{abbrev}_vchap{chapter}-{verse}"


def _parse_passage_id(passage_id: str) -> tuple[str, int, int]:
    """Parse OSB passage ID to get book, chapter, verse."""
    # Format: Gen_vchap1-1
    try:
        parts = passage_id.split("_vchap")
        abbrev = parts[0]
        ch_verse = parts[1].split("-")
        chapter = int(ch_verse[0])
        verse = int(ch_verse[1])
        book_id = _abbrev_to_book_id(abbrev)
        return book_id, chapter, verse
    except (IndexError, ValueError):
        return "", 0, 0


async def _get_passage_preview(passage_id: str) -> str | None:
    """Get preview text from OSB passage."""
    db = MongoDB.db_dox

    passage = await db.passages.find_one({"_id": passage_id}, {"text": 1})
    if passage and passage.get("text"):
        text = passage["text"]
        return text[:100] + "..." if len(text) > 100 else text
    return None


# Book name/abbreviation mappings
BOOK_NAMES = {
    "genesis": "Genesis", "exodus": "Exodus", "leviticus": "Leviticus",
    "numbers": "Numbers", "deuteronomy": "Deuteronomy", "joshua": "Joshua",
    "judges": "Judges", "ruth": "Ruth", "1kingdoms": "1 Kingdoms",
    "2kingdoms": "2 Kingdoms", "3kingdoms": "3 Kingdoms", "4kingdoms": "4 Kingdoms",
    "1chronicles": "1 Chronicles", "2chronicles": "2 Chronicles",
    "1ezra": "1 Ezra", "2ezra": "2 Ezra", "nehemiah": "Nehemiah",
    "tobit": "Tobit", "judith": "Judith", "esther": "Esther",
    "1maccabees": "1 Maccabees", "2maccabees": "2 Maccabees", "3maccabees": "3 Maccabees",
    "job": "Job", "psalms": "Psalms", "proverbs": "Proverbs",
    "ecclesiastes": "Ecclesiastes", "songofsongs": "Song of Songs",
    "wisdomofsolomon": "Wisdom of Solomon", "wisdomofsirach": "Wisdom of Sirach",
    "isaiah": "Isaiah", "jeremiah": "Jeremiah", "lamentations": "Lamentations",
    "baruch": "Baruch", "epistleofjeremiah": "Epistle of Jeremiah",
    "ezekiel": "Ezekiel", "daniel": "Daniel",
    "hosea": "Hosea", "joel": "Joel", "amos": "Amos", "obadiah": "Obadiah",
    "jonah": "Jonah", "micah": "Micah", "nahum": "Nahum", "habakkuk": "Habakkuk",
    "zephaniah": "Zephaniah", "haggai": "Haggai", "zechariah": "Zechariah", "malachi": "Malachi",
    "matthew": "Matthew", "mark": "Mark", "luke": "Luke", "john": "John", "acts": "Acts",
    "romans": "Romans", "1corinthians": "1 Corinthians", "2corinthians": "2 Corinthians",
    "galatians": "Galatians", "ephesians": "Ephesians", "philippians": "Philippians",
    "colossians": "Colossians", "1thessalonians": "1 Thessalonians", "2thessalonians": "2 Thessalonians",
    "1timothy": "1 Timothy", "2timothy": "2 Timothy", "titus": "Titus", "philemon": "Philemon",
    "hebrews": "Hebrews", "james": "James", "1peter": "1 Peter", "2peter": "2 Peter",
    "1john": "1 John", "2john": "2 John", "3john": "3 John", "jude": "Jude", "revelation": "Revelation",
}

BOOK_ABBREVS = {
    "genesis": "Gen", "exodus": "Exod", "leviticus": "Lev", "numbers": "Num",
    "deuteronomy": "Deut", "joshua": "Josh", "judges": "Judg", "ruth": "Ruth",
    "1kingdoms": "1Kgdms", "2kingdoms": "2Kgdms", "3kingdoms": "3Kgdms", "4kingdoms": "4Kgdms",
    "1chronicles": "1Chr", "2chronicles": "2Chr", "1ezra": "1Ezra", "2ezra": "2Ezra",
    "nehemiah": "Neh", "tobit": "Tob", "judith": "Jdt", "esther": "Esth",
    "1maccabees": "1Macc", "2maccabees": "2Macc", "3maccabees": "3Macc",
    "job": "Job", "psalms": "Ps", "proverbs": "Prov", "ecclesiastes": "Eccl",
    "songofsongs": "Song", "wisdomofsolomon": "Wis", "wisdomofsirach": "Sir",
    "isaiah": "Isa", "jeremiah": "Jer", "lamentations": "Lam", "baruch": "Bar",
    "epistleofjeremiah": "EpJer", "ezekiel": "Ezek", "daniel": "Dan",
    "hosea": "Hos", "joel": "Joel", "amos": "Amos", "obadiah": "Obad",
    "jonah": "Jonah", "micah": "Mic", "nahum": "Nah", "habakkuk": "Hab",
    "zephaniah": "Zeph", "haggai": "Hag", "zechariah": "Zech", "malachi": "Mal",
    "matthew": "Matt", "mark": "Mark", "luke": "Luke", "john": "John", "acts": "Acts",
    "romans": "Rom", "1corinthians": "1Cor", "2corinthians": "2Cor",
    "galatians": "Gal", "ephesians": "Eph", "philippians": "Phil",
    "colossians": "Col", "1thessalonians": "1Thess", "2thessalonians": "2Thess",
    "1timothy": "1Tim", "2timothy": "2Tim", "titus": "Titus", "philemon": "Phlm",
    "hebrews": "Heb", "james": "Jas", "1peter": "1Pet", "2peter": "2Pet",
    "1john": "1John", "2john": "2John", "3john": "3John", "jude": "Jude", "revelation": "Rev",
}

# Reverse mapping for abbreviation to book_id
ABBREV_TO_BOOK = {v: k for k, v in BOOK_ABBREVS.items()}


def _get_book_name(book_id: str) -> str:
    """Get display name for a book ID."""
    return BOOK_NAMES.get(book_id, book_id.title())


def _get_book_abbrev(book_id: str) -> str:
    """Get abbreviation for a book ID."""
    return BOOK_ABBREVS.get(book_id, book_id[:3].title())


def _abbrev_to_book_id(abbrev: str) -> str:
    """Convert abbreviation to book ID."""
    return ABBREV_TO_BOOK.get(abbrev, abbrev.lower())


def _format_passage_display(book_id: str, chapter: int, verse: int) -> str:
    """Format passage for display."""
    name = _get_book_name(book_id)
    return f"{name} {chapter}:{verse}"
