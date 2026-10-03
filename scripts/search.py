"""Query the knowledge base from the command line.

Usage:
    python scripts/search.py "leave policy for new joiners" --roles admin,HR
    python scripts/search.py "..." --answer          # full RAG answer
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal  # noqa: E402
from app.rag.pipeline import answer_question  # noqa: E402
from app.retrieval.hybrid_retriever import hybrid_retrieve  # noqa: E402
from app.schemas import QueryRequest  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search the ERAGA knowledge base")
    parser.add_argument("question", help="natural language question")
    parser.add_argument("--roles", default="admin", help="comma-separated ACL roles")
    parser.add_argument("--top-k", type=int, default=None, help="candidates to retrieve")
    parser.add_argument("--answer", action="store_true", help="generate a grounded answer")
    return parser.parse_args(argv)


async def run(args: argparse.Namespace) -> int:
    roles = [role.strip() for role in args.roles.split(",") if role.strip()]

    async with SessionLocal() as session:
        if args.answer:
            response = await answer_question(
                session, QueryRequest(question=args.question, top_k=args.top_k), roles=roles
            )
            print(f"\n{'=' * 70}\n{response.answer}\n{'=' * 70}")
            if response.citations:
                print("\nSources:")
                for citation in response.citations:
                    location = f"section {citation.section}" if citation.section else "unsectioned"
                    page = f", page {citation.page_number}" if citation.page_number else ""
                    print(f"  {citation.marker} {citation.document_title} ({location}{page})")
            print(
                f"\nretrieval={response.retrieval_ms}ms llm={response.llm_ms}ms "
                f"total={response.latency_ms}ms confidence={response.confidence} "
                f"tokens={response.tokens}"
            )
            return 0

        chunks = await hybrid_retrieve(session, args.question, roles=roles, top_k=args.top_k)
        if not chunks:
            print("no authorised chunks matched")
            return 1

        for index, item in enumerate(chunks, start=1):
            metadata = item.chunk.extra_metadata or {}
            source = metadata.get("source", "document")
            page = f"p{item.chunk.page_number}" if item.chunk.page_number else "-"
            section = item.chunk.section or "-"
            print(
                f"\n[{index}] {source} | {section} | page {page} "
                f"| fused={item.score:.4f} dense={item.dense_score:.4f} kw={item.keyword_score:.2f}"
            )
            print(f"    {item.content[:300]}")
        return 0


def main() -> int:
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
