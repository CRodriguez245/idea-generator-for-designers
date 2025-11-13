# Agent Instructions

Last updated: 2025-11-13

## Mission Context

- Project: **Idea Generator for Designers** — Streamlit-based AI assistant that reframes design challenges, generates sketch prompts, and proposes UI layout concepts.
- Target users: designers experimenting with rapid ideation; prototype starts local and graduates to a small web deployment.
- Core principle: keep solutions simple, reliable, and fast to iterate.

## Primary Responsibilities

1. **Feature Delivery**
   - Build the Streamlit interface with custom styling optimized for desktop.
   - Orchestrate GPT-4 and DALL·E calls to feel real-time; parallelize when it improves responsiveness.
   - Implement copy-friendly exports first; plan for PDF and JSON/CSV later.
2. **Data & State Management**
   - Use SQLite for persistence; retain sessions for six months.
   - Support optional name/email capture while respecting anonymous flows.
3. **Operational Guardrails**
   - Respect the $5/month OpenAI budget; log usage where practical.
   - Handle rate limits with friendly “please wait” messaging and retries.
   - Keep prompt templates in `prompts/` and document major changes in `decisions.md`.
4. **Security & Secrets**
   - Store API keys in local `.env`; use Streamlit secrets in hosted environments.
   - Never commit secrets; ensure `.env` and related files remain ignored.
5. **Observability**
   - Emit structured logs to stdout; surface errors via lightweight notification channels (email/Slack hooks, etc.).

## Collaboration Etiquette

- Update `decisions.md` whenever architectural or process choices evolve.
- Maintain concise commit messages and push to `main` after verifying lint/tests.
- Favor incremental, testable changes; document assumptions in PR descriptions or commit summaries.
- When uncertain, prompt the human collaborator for clarifications instead of guessing.

## Definition of Done Checklist

- [ ] Feature or fix delivered with tests or manual verification notes.
- [ ] No secrets or private data leaked.
- [ ] README/decisions updated if scope, workflow, or expectations changed.
- [ ] Lints/tests pass locally (or known issues documented).
- [ ] Commit pushed and ready for review or release.

