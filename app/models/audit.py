from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.document import Base


class QueryAudit(Base):
    """One row per answered query — the cost/latency/quality trail."""

    __tablename__ = "query_audits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(nullable=True)
    roles: Mapped[str | None] = mapped_column(nullable=True)

    query: Mapped[str] = mapped_column(nullable=False)
    chunks_retrieved: Mapped[int] = mapped_column(default=0, nullable=False)
    top_k: Mapped[int] = mapped_column(default=0, nullable=False)

    retrieval_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    llm_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    total_ms: Mapped[int] = mapped_column(default=0, nullable=False)

    input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(default=0.0, nullable=False)

    llm_model: Mapped[str | None] = mapped_column(nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
