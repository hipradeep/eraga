-- ERAGA initial schema (PostgreSQL 16 + pgvector)
-- Applied automatically by app/models/__init__.py on startup in dev.
-- For production use Alembic migrations instead.

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------- RBAC
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    full_name   TEXT NOT NULL,
    department  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roles (
    id    UUID PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- ---------------------------------------------------------------- Documents
CREATE TABLE IF NOT EXISTS documents (
    id             UUID PRIMARY KEY,
    name           TEXT NOT NULL,
    doc_type       TEXT NOT NULL,
    source_uri     TEXT,
    department     TEXT,
    classification TEXT NOT NULL DEFAULT 'INTERNAL',
    version        TEXT,
    allowed_roles  TEXT[] NOT NULL DEFAULT '{}',
    checksum       TEXT,
    chunk_count    INTEGER NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'pending',
    error          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_department ON documents (department);
CREATE INDEX IF NOT EXISTS idx_documents_status      ON documents (status);

-- ---------------------------------------------------------------- Chunks + vectors
CREATE TABLE IF NOT EXISTS document_chunks (
    id            UUID PRIMARY KEY,
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INTEGER NOT NULL,
    content       TEXT NOT NULL,
    embedding     vector(768),
    page_number   INTEGER,
    section       TEXT,
    char_count    INTEGER NOT NULL DEFAULT 0,
    metadata      JSONB NOT NULL DEFAULT '{}',
    allowed_roles TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_roles        ON document_chunks USING gin (allowed_roles);
CREATE UNIQUE INDEX IF NOT EXISTS uq_chunks_document_index
    ON document_chunks (document_id, chunk_index);

-- HNSW index: create AFTER bulk loading, it is slow to build on tiny tables.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id         UUID PRIMARY KEY,
    user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    title      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    sources         JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, created_at);

-- ---------------------------------------------------------------- Feedback
CREATE TABLE IF NOT EXISTS feedback (
    id         UUID PRIMARY KEY,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    rating     INTEGER NOT NULL CHECK (rating IN (-1, 1)),
    comment    TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- Audit
CREATE TABLE IF NOT EXISTS query_audits (
    id                SERIAL PRIMARY KEY,
    user_id           TEXT,
    roles             TEXT,
    query             TEXT NOT NULL,
    chunks_retrieved  INTEGER NOT NULL DEFAULT 0,
    top_k             INTEGER NOT NULL DEFAULT 0,
    retrieval_ms      INTEGER NOT NULL DEFAULT 0,
    llm_ms            INTEGER NOT NULL DEFAULT 0,
    total_ms          INTEGER NOT NULL DEFAULT 0,
    input_tokens      INTEGER NOT NULL DEFAULT 0,
    output_tokens     INTEGER NOT NULL DEFAULT 0,
    cost_usd          DOUBLE PRECISION NOT NULL DEFAULT 0,
    llm_model         TEXT,
    embedding_model   TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_query_audits_created ON query_audits (created_at DESC);