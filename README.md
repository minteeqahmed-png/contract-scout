# Contract Scout

Contract Scout is an AI-powered legal contract auditor. It processes PDF contracts, extracts their text/clauses, and runs them against a predefined compliance playbook to identify legal risks, missing clauses, and financial exposure. 

## Features
- **PDF Extraction**: Upload a PDF contract and extract readable text/clauses using `pdfplumber`.
- **AI Auditing**: Uses Google's Gemini LLMs (via OpenAI compatibility layer) to audit clauses against rules defined in `config/compliance_playbook.json`.
- **Hybrid Search**: Leverages `ChromaDB` and `sentence-transformers` to index and retrieve relevant contract clauses.
- **Redline Generation**: Generates actionable, redlined `.docx` documents for the audited contract.
- **FastAPI Backend**: Provides a simple and fast REST API, served via Uvicorn.

## Getting Started

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and add your API keys:
   ```env
   OPENAI_API_KEY=your_gemini_or_openai_api_key
   OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   LLM_MODEL=gemini-1.5-pro-latest
   ```
5. Run the server:
   ```bash
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```
6. Visit `http://127.0.0.1:8000` to access the application.

## Playbook Configuration
You can customize the auditing rules by editing `config/compliance_playbook.json`. Add or modify rules to check for different compliance standards.
