# Build Plan

Last updated: 2025-11-13

## Phase 1 — Foundation (Week 1)

1. **Repo Hygiene**
   - Ensure `.env` ignored, initialize virtual environment scaffold.
   - Create placeholder structure matching README (`app.py`, `prompts/`, `utils/`, etc.).
2. **Prompt Templates**
   - Draft initial `hmw_prompt.txt`, `visual_prompt.txt`, `layout_prompt.txt`.
   - Validate with manual GPT calls to confirm tone/structure.
3. **Streamlit Skeleton**
   - Basic layout with sections for input, loading states, and results.
   - Stub functions for each generation step (no API calls yet).

## Phase 2 — AI Integration (Week 2)

1. **OpenAI Helper Utilities**
   - Implement `utils/openai_helpers.py` with GPT-4 and DALL·E wrappers, budget logging.
   - Add concurrency support for parallel GPT+DALL·E requests.
2. **End-to-End Flow**
   - Wire helpers into `app.py`; stream partial results as they finish.
   - Implement graceful rate-limit handling and retries.
3. **Session Persistence**
   - Introduce SQLite schema + helper functions (`utils/session_store.py`).
   - Capture optional name/email and generated outputs per session.

## Phase 3 — UX Polish (Week 3)

1. **Custom Styling**
   - Apply desktop-first CSS overrides, ensure responsive fallbacks.
2. **Export Controls**
   - Copy-to-clipboard buttons per section + “copy all.”
   - Scaffold future PDF/JSON export handlers (even if placeholder).
3. **Observability**
   - Add structured logging, error tracing, and basic usage metrics.

## Phase 4 — Hardening & Deploy (Week 4)

1. **Testing & QA**
   - Manual QA scripts, light automated tests for helpers.
   - Verify budget guardrails and session retention logic.
2. **Documentation**
   - Update README, `decisions.md`, prompt docs.
   - Add “getting started” video/GIF if time allows.
3. **Deployment**
   - Configure Streamlit Cloud app, secrets, and smoke tests.
   - Invite pilot users; set reminder to review usage after first week.

