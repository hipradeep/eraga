# 🧠 Eraga — Enterprise RAG Assistant

> **Eraga** = **E**nterprise **RAG** **A**ssistant  
> Intelligent, scalable, and production-ready Retrieval-Augmented Generation for the enterprise.

---

## 📌 Overview

**Eraga** is an enterprise-grade **Retrieval-Augmented Generation (RAG)** assistant that combines the power of large language models (LLMs) with intelligent document retrieval to deliver accurate, context-aware answers from your organization's private knowledge base.

Whether you're searching through internal documents, SOPs, policies, or product data — Eraga finds, retrieves, and generates precise responses grounded in your enterprise data.

---

## ✨ Key Features

- 🔍 **Semantic Search** — Vector-based retrieval using embeddings for contextual understanding
- 🤖 **LLM-Powered Answers** — Generate responses grounded in retrieved enterprise documents
- 📂 **Multi-Source Ingestion** — Support for PDFs, DOCX, HTML, databases, and more
- 🔐 **Enterprise Security** — Role-based access control and data privacy guardrails
- 📊 **Audit & Traceability** — Every answer traceable back to its source document
- ⚡ **Scalable Architecture** — Designed for high-concurrency enterprise workloads
- 🌐 **API-First Design** — Easy integration with existing enterprise systems

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Eraga RAG Pipeline                    │
├──────────────┬───────────────────┬───────────────────────┤
│  Data Layer  │  Retrieval Layer  │   Generation Layer    │
│              │                   │                       │
│  Documents   │  Vector Store     │   LLM (Gemini /       │
│  PDFs, DOCX  │  Embeddings       │   GPT / Claude)       │
│  Databases   │  Semantic Search  │   Prompt Engineering  │
│  APIs        │  Re-ranking       │   Response Grounding  │
└──────────────┴───────────────────┴───────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Git
- API keys for your chosen LLM provider (Gemini / OpenAI / Anthropic)

### Clone the Repository

```bash
git clone https://github.com/hipradeep/eraga.git
cd eraga
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Run Eraga

```bash
python main.py
```

---

## 📁 Project Structure

```
eraga/
├── README.md               # Project documentation
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── ingestion/              # Document ingestion & chunking
│   ├── loaders.py
│   └── chunker.py
├── retrieval/              # Vector store & semantic search
│   ├── embeddings.py
│   └── retriever.py
├── generation/             # LLM integration & prompting
│   ├── llm_client.py
│   └── prompt_templates.py
├── api/                    # REST API layer
│   └── routes.py
└── tests/                  # Unit & integration tests
```

---

## 🔧 Tech Stack

| Layer       | Technology                           |
|-------------|---------------------------------------|
| Language    | Python 3.10+                         |
| LLM         | Google Gemini / OpenAI GPT / Claude  |
| Embeddings  | Vertex AI / OpenAI Embeddings         |
| Vector DB   | ChromaDB / Pinecone / Weaviate        |
| API         | FastAPI                              |
| Storage     | Google Cloud Storage / AWS S3         |

---

## 🗺️ Roadmap

### Phase 1 — Foundation ✅ *(Completed)*
| # | Task | Status |
|---|------|--------|
| 1.1 | Project initialization & repo setup | ✅ Done |
| 1.2 | README & documentation | ✅ Done |
| 1.3 | Define architecture & tech stack | ✅ Done |

---

### Phase 2 — Data Ingestion 🔄 *(In Progress)*
| # | Task | Status |
|---|------|--------|
| 2.1 | PDF / DOCX / TXT document loaders | 🔄 In Progress |
| 2.2 | HTML & web page scraper | ⬜ Planned |
| 2.3 | Database & API connectors | ⬜ Planned |
| 2.4 | Document chunking & preprocessing | ⬜ Planned |
| 2.5 | Metadata extraction & tagging | ⬜ Planned |

---

### Phase 3 — Retrieval Engine ⬜ *(Planned)*
| # | Task | Status |
|---|------|--------|
| 3.1 | Embedding generation (Vertex AI / OpenAI) | ⬜ Planned |
| 3.2 | Vector store integration (ChromaDB / Pinecone) | ⬜ Planned |
| 3.3 | Semantic similarity search | ⬜ Planned |
| 3.4 | Hybrid search (dense + sparse / BM25) | ⬜ Planned |
| 3.5 | Re-ranking & relevance scoring | ⬜ Planned |

---

### Phase 4 — Generation & RAG Pipeline ⬜ *(Planned)*
| # | Task | Status |
|---|------|--------|
| 4.1 | LLM integration (Gemini / GPT / Claude) | ⬜ Planned |
| 4.2 | Prompt engineering & templates | ⬜ Planned |
| 4.3 | End-to-end RAG pipeline | ⬜ Planned |
| 4.4 | Citation & source attribution | ⬜ Planned |
| 4.5 | Hallucination detection & guardrails | ⬜ Planned |

---

### Phase 5 — API & Integration ⬜ *(Planned)*
| # | Task | Status |
|---|------|--------|
| 5.1 | REST API with FastAPI | ⬜ Planned |
| 5.2 | Authentication & API key management | ⬜ Planned |
| 5.3 | Streaming response support | ⬜ Planned |
| 5.4 | Webhook & event notifications | ⬜ Planned |
| 5.5 | SDK for Python / JavaScript | ⬜ Planned |

---

### Phase 6 — Enterprise Features ⬜ *(Planned)*
| # | Task | Status |
|---|------|--------|
| 6.1 | Role-based access control (RBAC) | ⬜ Planned |
| 6.2 | Multi-tenant support | ⬜ Planned |
| 6.3 | Audit logs & traceability | ⬜ Planned |
| 6.4 | Data privacy & PII masking | ⬜ Planned |
| 6.5 | SSO / LDAP / OAuth2 integration | ⬜ Planned |

---

### Phase 7 — UI & DevOps ⬜ *(Planned)*
| # | Task | Status |
|---|------|--------|
| 7.1 | Web UI chat dashboard | ⬜ Planned |
| 7.2 | Admin panel for document management | ⬜ Planned |
| 7.3 | CI/CD pipeline (GitHub Actions) | ⬜ Planned |
| 7.4 | Docker & container support | ⬜ Planned |
| 7.5 | Cloud deployment (GCP / AWS) | ⬜ Planned |

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**Built with ❤️ by [hipradeep](https://github.com/hipradeep)**  
*Empowering enterprises with intelligent, grounded AI.*

</div>
