"""One-shot database bootstrap: apply infra/schema.sql and create the vector index."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.models import Base  # noqa: F401,E402

SCHEMA_SQL = ROOT / "infra" / "schema.sql"


def split_statements(sql: str) -> list[str]:
    """Split a DDL script into individual statements.

    asyncpg rejects multi-statement prepared statements, so the script must be fed
    one statement at a time. This splitter is deliberately simple and assumes DDL
    only: no function bodies, no dollar-quoting. It does respect single-quoted
    literals and `--` comments.
    """
    statements: list[str] = []
    buffer: list[str] = []
    in_single = False
    in_line_comment = False

    for char in sql:
        if in_line_comment:
            buffer.append(char)
            if char == "\n":
                in_line_comment = False
            continue

        if char == "-" and not in_single:
            in_line_comment = True
            buffer.append(char)
            continue

        if char == "'":
            in_single = not in_single
            buffer.append(char)
            continue

        if char == ";" and not in_single:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            continue

        buffer.append(char)

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)

    return [
        s
        for s in statements
        if s
        and not all(line.strip().startswith("--") or not line.strip() for line in s.splitlines())
    ]


async def main() -> int:
    if not SCHEMA_SQL.exists():
        print(f"missing {SCHEMA_SQL}")
        return 1

    statements = split_statements(SCHEMA_SQL.read_text(encoding="utf-8"))

    async with engine.begin() as conn:
        for index, statement in enumerate(statements, start=1):
            try:
                await conn.execute(text(statement))
            except Exception as exc:  # noqa: BLE001
                first_line = statement.lstrip().splitlines()[0][:70]
                print(f"statement {index} failed ({first_line}...): {exc}")
                raise
    print(f"applied {len(statements)} statements from {SCHEMA_SQL.name}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("SQLAlchemy metadata synced")

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_chunks_embedding_hnsw'")
        )
        vector_index = bool(result.scalar_one())
    print(f"pgvector HNSW index: {'present' if vector_index else 'missing'}")

    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
