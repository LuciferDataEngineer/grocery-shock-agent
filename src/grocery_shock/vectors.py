"""Build a DuckDB VSS HNSW index over the insight notes."""

from __future__ import annotations

from grocery_shock.embed import DIM, embed
from grocery_shock.paths import insights_dir
from grocery_shock.warehouse import connect


def _documents() -> list[dict[str, str]]:
    documents = []
    for path in sorted(insights_dir().glob("*.md")):
        text = path.read_text()
        title, _, body = text.partition("\n\n")
        documents.append(
            {
                "doc_id": path.stem,
                "title": title.removeprefix("# ").strip(),
                "body": body.strip(),
            }
        )
    if not documents:
        raise RuntimeError("no insight notes to index")
    return documents


def build_vector_index() -> int:
    documents = _documents()
    connection = connect(load_vss=True)
    try:
        connection.execute("CREATE SCHEMA IF NOT EXISTS memory")
        connection.execute("DROP TABLE IF EXISTS memory.insight_chunks")
        connection.execute(
            f"""
            CREATE TABLE memory.insight_chunks (
                doc_id VARCHAR,
                title VARCHAR,
                body VARCHAR,
                embedding FLOAT[{DIM}]
            )
            """
        )
        for document in documents:
            vector = embed(f"{document['title']}. {document['body']}")
            connection.execute(
                "INSERT INTO memory.insight_chunks VALUES (?, ?, ?, ?)",
                [document["doc_id"], document["title"], document["body"], vector],
            )
        connection.execute(
            """
            CREATE INDEX insight_hnsw
            ON memory.insight_chunks
            USING HNSW (embedding)
            WITH (metric = 'cosine')
            """
        )
        connection.execute("CHECKPOINT")
    finally:
        connection.close()
    return len(documents)
