# 🛡️ ALFRED AI — Intelligent Document Workspace

> **Your knowledge, connected. Your decisions, better informed.**

An enterprise-grade, air-gapped RAG (Retrieval-Augmented Generation) document assistant and business intelligence workspace. Upload corporate PDFs, execute deep semantic search, generate source-grounded answers with verifiable citations (`[S1]`, `[S2]`), and extract executive briefs — 100% locally with zero cloud dependencies.

Featuring the **Aurora Mint** executive design system inspired by modern analytics platforms, with custom Butler Crest branding, stationary embossed geometric textures, and real-time Plotly data visualizations.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 📄 **Document Intake** | Multi-file PDF ingestion with SHA-256 deduplication, PyMuPDF extraction, and real-time progress callbacks |
| 🧩 **Sliding-Window Chunking** | Configurable overlapping text chunks with full page-level provenance metadata |
| 🔍 **Vector Retrieval** | FAISS `IndexFlatIP` index with normalized 384-dimensional dense embeddings (`all-MiniLM-L6-v2`) |
| 💬 **Grounded Chat** | Local LLM generation (via Ollama) with strict citation verification and expandable evidence cards |
| 📝 **Dual-Engine Summaries** | Instant extractive summarization for offline speeds + Map-Reduce AI synthesis for executive briefs |
| 📊 **Workspace Analytics** | Real Plotly charts for corpus distribution, ingestion ledgers, and query timelines (no mock data) |
| 🧪 **Retrieval Evaluation** | Automated Hit Rate@k and Mean Reciprocal Rank (MRR) benchmarking suite |
| 🛡️ **Air-Gapped Privacy** | 100% on-premise execution; SQLite persistence and local FAISS indices survive app restarts |
| 🎨 **Aurora Mint UI** | Pearl mint surfaces, deep jade branding, semantic analytics cards, and stationary embossed scale textures |

---

## 🏗️ Architecture

```
User Browser
     │
     ▼
Streamlit (app.py + pages/)
     │
     ├── PDF Upload → pdf_processor.py → chunk_pages()
     │                                         │
     │                                         ▼
     │                               vector_store.py → FAISS index
     │
     ├── Chat → rag_engine.query()
     │           ├── vector_store.search()  (retrieve top-k chunks)
     │           └── llm_service.generate_answer()  (Ollama API)
     │
     ├── Summary → summarizer.summarise_document()  (map-reduce via Ollama)
     │
     ├── Analytics → analytics.py → SQLite → Plotly charts
     │
     └── Evaluation → evaluation.py → Hit Rate, MRR
              │
              ▼
         SQLite (database.py) ← all metadata, queries, activity
```

---

## 🖥️ Requirements

- **Python 3.11+** (tested on 3.13)
- **[Ollama](https://ollama.com/download)** — local LLM server
- ~4 GB disk for model weights (llama3.2:3b)
- ~500 MB for embedding model (all-MiniLM-L6-v2, downloads on first use)

---

## ⚡ Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/YOUR_USERNAME/rag-document-assistant.git
cd rag-document-assistant
pip install -r requirements.txt
```

### 2. Configure (optional)

```bash
cp .env.example .env
# Edit .env to customise OLLAMA_MODEL, chunk sizes, etc.
```

### 3. Install and start Ollama

```bash
# Download Ollama from https://ollama.com/download
# Then pull the model:
ollama pull llama3.2:3b
# Ollama starts automatically on Windows, or run:
ollama serve
```

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📁 Project Structure

```
rag-document-assistant/
├── app.py                  # Main dashboard (entry point)
├── config.py               # All configuration from .env
├── rag_engine.py           # End-to-end pipeline coordinator
├── pdf_processor.py        # PDF extraction and chunking
├── vector_store.py         # FAISS embeddings and search
├── llm_service.py          # Ollama integration
├── summarizer.py           # Map-reduce summarisation
├── analytics.py            # Data aggregation for charts
├── evaluation.py           # Hit Rate, MRR, citation checks
├── database.py             # SQLite persistence layer
├── utils.py                # Shared helpers
├── requirements.txt
├── .env.example
├── evaluation_cases.json   # Add your test Q&A pairs here
├── pages/
│   ├── 1_Chat.py           # Chat interface
│   ├── 2_Documents.py      # Document library
│   ├── 3_Summaries.py      # Summary workspace
│   ├── 4_Analytics.py      # Analytics dashboard
│   ├── 5_Evaluation.py     # Retrieval evaluation
│   └── 6_Settings.py       # Settings and about
├── components/
│   ├── sidebar.py          # Persistent sidebar
│   ├── metric_cards.py     # KPI cards
│   ├── source_cards.py     # Citation source cards
│   └── charts.py           # Plotly chart builders
├── styles/
│   └── custom.css          # Premium dark theme CSS
├── tests/                  # pytest test suite
│   ├── test_pdf_processor.py
│   ├── test_chunking.py
│   ├── test_vector_store.py
│   ├── test_citations.py
│   └── test_evaluation.py
└── data/
    ├── uploads/            # Saved PDFs (gitignored)
    └── indexes/            # FAISS index files (gitignored)
```

---

## 🧪 Running Tests

```bash
# From the project root
pytest tests/ -v

# Run only fast tests (skip embedding model load)
pytest tests/test_pdf_processor.py tests/test_citations.py tests/test_evaluation.py -v
```

> **Note:** `test_vector_store.py` tests load the embedding model (~90 MB) on first run. Requires internet access once.

---

## 🔧 Configuration

All options are set via environment variables (copy `.env.example` to `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model to use for chat and summaries |
| `DEFAULT_CHUNK_SIZE` | `900` | Characters per text chunk |
| `DEFAULT_CHUNK_OVERLAP` | `150` | Overlap between adjacent chunks |
| `DEFAULT_TOP_K` | `5` | Chunks retrieved per query |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum PDF file size |

---

## 📊 Evaluation

Add test cases to `evaluation_cases.json`:

```json
[
  {
    "question": "What is the main finding?",
    "expected_page": 3,
    "doc_id": null
  }
]
```

Then run evaluation from the **Evaluation** page in the app.

**Automated metrics:**
- **Hit Rate @ k** — is the correct page in the top-k results?
- **MRR** — Mean Reciprocal Rank across all test cases

**Not automated:** Answer faithfulness requires human review.

---

## ⚠️ Known Limitations

- Scanned/image-only PDFs: No OCR support. Text extraction returns empty for image-based PDFs.
- Long PDFs: Summarisation uses the first 20 chunks (configurable). Full-document summarisation would require more LLM calls.
- Cloud deployment: The local Ollama endpoint is not accessible from cloud-hosted Streamlit. You would need to configure a remote Ollama endpoint or use a different LLM provider.
- Context window: For very long answers, the context is capped at ~6,000 characters to stay within the local model's limits.

---

## 🛡️ Privacy

- All documents are processed on **your local machine**.
- PDFs are stored in `data/uploads/` (gitignored).
- The SQLite database lives in `data/rag_assistant.db` (gitignored).
- No data is sent to external servers after initial model downloads.

---

## 🚀 Deployment Options

### Local (recommended)
Run `streamlit run app.py` — everything works offline after first setup.

### Cloud (Streamlit Community Cloud / Hugging Face Spaces)
You must provide a **remote Ollama endpoint** or swap the LLM service for a cloud API.
Set `OLLAMA_HOST` to your remote server URL. Never commit API keys — use platform secrets management.

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Run tests: `pytest tests/ -v`
4. Open a pull request

---

## 📄 License

MIT License — see LICENSE file for details.
