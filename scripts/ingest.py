"""Ingest documents from the command line.

Usage:
    python scripts/ingest.py data/samples/*.pdf --department HR --roles admin,HR
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal  # noqa: E402
from app.ingestion.pipeline import ingest_file  # noqa: E402
from app.retrieval.vector_store import ensure_vector_index  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest documents into ERAGA")
    parser.add_argument("paths", nargs="+", help="files or directories to ingest")
    parser.add_argument("--department", default=None, help="department tag, e.g. HR")
    parser.add_argument("--roles", default="admin", help="comma-separated ACL roles")
    parser.add_argument("--classification", default="INTERNAL", help="PUBLIC|INTERNAL|CONFIDENTIAL")
    parser.add_argument("--version", default=None, help="document version string")
    return parser.parse_args(argv)


def expand(paths: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            resolved.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        else:
            resolved.append(path)
    return resolved


async def run(args: argparse.Namespace) -> int:
    roles = [role.strip() for role in args.roles.split(",") if role.strip()]
    files = expand(args.paths)
    if not files:
        print("no files found")
        return 1

    failures = 0
    async with SessionLocal() as session:
        await ensure_vector_index(session)
        for file in files:
            result = await ingest_file(
                session,
                file,
                department=args.department,
                allowed_roles=roles,
                classification=args.classification,
                version=args.version,
            )
            status = "OK " if result.ok else "FAIL"
            if result.ok:
                print(f"[{status}] {result.name}: {result.chunk_count} chunks")
            else:
                failures += 1
                print(f"[{status}] {result.name}: {result.error}")

    print(f"\n{len(files) - failures}/{len(files)} documents ingested successfully")
    return 1 if failures else 0


def main() -> int:
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
