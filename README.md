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

- [x] Project initialization
- [x] README & documentation
- [ ] Document ingestion pipeline
- [ ] Embedding & vector store integration
- [ ] RAG pipeline (retrieval + generation)
- [ ] REST API with FastAPI
- [ ] Web UI dashboard
- [ ] Multi-tenant enterprise support
- [ ] CI/CD pipeline

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
