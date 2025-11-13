# Build Plan

Last updated: 2025-11-13

## Phase 1 — Foundation (Week 1)

### Goals
- Establish repo scaffolding, environment setup, and core files.
- Define prompt templates and manually verify expected outputs.
- Build a Streamlit skeleton with placeholder data flows.

### Tasks & Owners

1. **Environment & Tooling**
   - [ ] Create `requirements.txt` with baseline deps (`streamlit`, `openai`, `python-dotenv`, `sqlalchemy`, etc.).
   - [ ] Document environment setup in README and `plan.md`.
   - [ ] Configure VS Code/Cursor settings (formatters, linting rules if any).
2. **Directory & File Scaffolding**
   - [ ] Generate directories: `prompts/`, `utils/`, `assets/`, `data/`.
   - [ ] Add placeholder modules:
     - `app.py` with TODO comments for each section.
     - `utils/__init__.py`, `utils/openai_helpers.py`, `utils/ui_helpers.py`, `utils/session_store.py`.
     - `prompts/hmw_prompt.txt`, `prompts/visual_prompt.txt`, `prompts/layout_prompt.txt` (draft content).
   - [ ] Create `.streamlit/config.toml` to prepare for custom theming.
3. **Prompt Prototyping**
   - [ ] Draft initial prompt wording using guidance from README.
   - [ ] Manually call GPT-4 via CLI/notebook to ensure target tone/structure (log outputs in `/data/prompt_tests/`).
   - [ ] Iterate until responses align with design goals; capture learnings in `decisions.md`.
4. **Streamlit Skeleton**
   - [ ] Compose base layout with columns for HMW, sketches, layouts.
   - [ ] Include input form (challenge text, optional name/email).
   - [ ] Add placeholders for progress indicators/loading spinners.
   - [ ] Provide mock data rendering to validate UI structure.
5. **Process Checkpoints**
   - [ ] End-of-week review: verify scaffolding matches README structure.
   - [ ] Update `decisions.md` with prompt finalization notes.

## Phase 2 — AI Integration (Week 2)

### Goals
- Implement robust helper utilities for GPT-4 and DALL·E calls.
- Connect UI to live AI outputs with streaming behavior.
- Persist generated sessions in SQLite with budget tracking.

### Tasks & Owners

1. **OpenAI Helper Layer**
   - [ ] Implement `OpenAIClient` wrapper handling retries, logging, and budget accumulation.
   - [ ] Provide async interfaces for GPT (`generate_text`) and DALL·E (`generate_images`).
   - [ ] Add configurable rate limit handling (backoff, friendly error messages).
   - [ ] Write unit tests/mocks for helper functions.
2. **Streaming & Parallelization**
   - [ ] Use `asyncio` or Streamlit `st.session_state` patterns to stream partial results.
   - [ ] Parallelize GPT sketch prompt generation and DALL·E image calls.
   - [ ] Ensure UI updates progressively with skeleton loaders.
3. **Session Persistence**
   - [ ] Design SQLite schema: `sessions`, `generations`, `assets`.
   - [ ] Implement CRUD helpers in `session_store.py`.
   - [ ] Integrate persistence into flow (create session on submit, update as steps complete).
   - [ ] Schedule nightly cleanup task (CLI or Streamlit script) to purge >6 month data.
4. **Budget Monitoring**
   - [ ] Track API usage cost per session; log warnings when approaching $5 monthly cap.
   - [ ] Add admin view or log summary of recent usage.
5. **Validation & Review**
   - [ ] Test end-to-end flow with real API; capture screenshots for documentation.
   - [ ] Log any prompt refinements back to `prompts/` and `decisions.md`.

## Phase 3 — UX Polish (Week 3)

### Goals
- Elevate the UI with custom styling and interaction polish.
- Deliver reliable export mechanisms and helpful user feedback.
- Establish baseline observability (logging + optional notifications).

### Tasks & Owners

1. **Design System & Styling**
   - [ ] Create custom CSS in `.streamlit/config.toml` and/or `assets/styles.css`.
   - [ ] Implement consistent typography, spacing, and color palette aligned with brand.
   - [ ] Ensure responsive fallback (single column) degrades gracefully on tablet.
   - [ ] Add subtle animations for loading and reveal states.
2. **Interaction Enhancements**
   - [ ] Add copy-to-clipboard buttons with toast confirmations.
   - [ ] Build “copy all” aggregator that compiles current session into Markdown.
   - [ ] Introduce manual refresh/regenerate controls for each section.
   - [ ] Surface optional name/email prominently with explanation of benefits.
3. **Export Roadmap Execution**
   - [ ] Implement placeholder handlers for PDF/JSON exports (non-functional UI stub).
   - [ ] Define data schema for export to ensure consistency.
4. **Observability & Messaging**
   - [ ] Configure structured logging including session IDs and timings.
   - [ ] Set up error notification channel (email/Slack), even if manual for now.
   - [ ] Provide user-facing error modals/popovers with troubleshooting tips.
5. **UX Review**
   - [ ] Conduct usability walkthrough; gather feedback from at least one designer.
   - [ ] Update `decisions.md` with styling choices and feedback outcomes.

## Phase 4 — Hardening & Deploy (Week 4)

### Goals
- Tighten reliability, document usage, and prepare Streamlit Cloud deployment.
- Establish testing routines and pilot rollout process.

### Tasks & Owners

1. **Testing & QA**
   - [ ] Write automated tests for helper modules (OpenAI client, session store).
   - [ ] Develop manual QA checklist covering edge cases (empty inputs, retries).
   - [ ] Verify budget guardrail triggers under simulated high usage.
   - [ ] Ensure cleanup script removes old session data without impacting active users.
2. **Documentation & Enablement**
   - [ ] Refresh README with setup steps, screenshots, and known limitations.
   - [ ] Update `agent_instructions.md` to reflect any new workflows.
   - [ ] Record a short Loom or GIF demonstrating the main flow.
   - [ ] Publish a change log entry summarizing phases completed.
3. **Deployment & Rollout**
   - [ ] Configure Streamlit Cloud app, including secrets and environment variables.
   - [ ] Run smoke tests on deployed environment (latency, image rendering).
   - [ ] Invite pilot users; collect feedback via form or email.
   - [ ] Schedule post-launch review to assess API usage and performance after first week.
4. **Future Planning**
   - [ ] Capture backlog items (PDF export implementation, mobile support, auth).
   - [ ] Prioritize next-phase tasks based on pilot feedback.

