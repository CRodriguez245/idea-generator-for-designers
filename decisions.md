# Decisions Log

## 2025-11-13 – Tech Plan Summary

- **Runtime & Hosting**
  - Streamlit app runs locally first, then deploy to Streamlit Cloud for a small group.
- **Frontend Experience**
  - Streamlit UI enhanced with custom CSS, optimized for desktop; stream each section as results arrive for a real-time feel.
- **AI Orchestration**
  - `app.py` coordinates sequential GPT-4 and DALL·E 3 calls using a single backend API key, caching structured responses in memory.
- **Persistence Layer**
  - Lightweight database (SQLite or TinyDB) stores sessions, generated ideas, and timestamps keyed to anonymous session IDs.
- **Export Mechanics**
  - Buttons for copying individual sections plus a “copy all” aggregate export in plain text or markdown.
- **Optional Enhancements**
  - Add authentication later via Streamlit secrets or OAuth; polish responsive layout once the desktop experience is solid.

## 2025-11-13 – Operational Guardrails

- **OpenAI Budget**
  - Cap usage at ~$5/month for v1; monitor before inviting more users.
- **Storage & Retention**
  - Use SQLite; keep session records for up to six months before pruning.
- **Session Identity**
  - Allow visitors to optionally enter a name/email; otherwise assign anonymous IDs.
- **Secrets Management**
  - Store keys in local `.env` during development and Streamlit Cloud secrets in deployment.
- **Rate Limiting UX**
  - On API rate-limit errors, show a friendly “please wait” message and retry guidance.
- **Prompt Management**
  - Maintain prompt templates in `prompts/`; log major changes in `decisions.md`.
- **Observability**
  - Structured logs to stdout plus lightweight error notifications (email/Slack) as needed.
- **Performance Strategy**
  - Parallelize GPT-4 and DALL·E calls where possible to keep the experience snappy.
- **Export Roadmap**
  - Next formats after copy-paste: PDF and downloadable JSON/CSV bundles.

