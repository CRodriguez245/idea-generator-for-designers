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

