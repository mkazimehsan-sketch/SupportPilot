# SupportPilot — Intelligent Support Ticket Workflow

**Stack & Scale Remote Internship 2026 · Week 02 · AI Agents & Automation**  
**Final handover: Friday, 6 November 2026**

SupportPilot is a small, auditable support-ticket workflow for a support coordinator. It accepts customer requests, stores them in SQLite, generates explainable category and priority suggestions, recommends a team, and requires human confirmation before assignment. Assigned tickets can be resolved with a named resolver and a resolution note.

## Weekly progress

- [x] **Day 1 — Ticket model and intake:** ticket fields, validation, state model, CLI/HTTP intake, SQLite persistence, event log and workflow diagram.
- [x] **Day 2 — Classification:** weighted keyword rules, priority suggestions, reasons and `Unknown/Needs Review` fallback.
- [x] **Day 3 — Routing and human approval:** category-to-team mapping, review queue, approval/change action and audit events.
- [x] **Day 4 — Reliability:** guarded resolution, duplicate intake rejection, invalid transition handling and failure tests.
- [x] **Day 5 — Final handover:** polished CLI messages and filtered listing, final operating documentation, repeatable demo script and narration guide.

## Quick start

**Requirements:** Python 3.10 or newer. The core project uses only the Python standard library. No paid AI API, external model, or environment secrets are needed.

Open a terminal in the folder containing this README:

```bash
python --version
python -m unittest discover -s tests -v
python -m supportpilot.cli --help
```

Run a complete, repeatable fictional-data walkthrough:

```bash
bash scripts/run_day5_demo.sh
```

The demo creates `data/day5_demo.db`, which is ignored by Git. Delete it or rerun the script to start over.

## Main operator commands

```bash
# Create and classify
python -m supportpilot.cli create --subject "Refund request" --message "I was charged twice and need a refund." --contact CUST-5101
python -m supportpilot.cli classify --all

# Review and human-confirm assignment
python -m supportpilot.cli queue
python -m supportpilot.cli start-review --ticket TCK-0001 --reviewer "Support Coordinator"
python -m supportpilot.cli confirm --ticket TCK-0001 --reviewer "Support Coordinator"

# Resolve and inspect history
python -m supportpilot.cli resolve --ticket TCK-0001 --resolver "Support Coordinator" --resolution "Refund processed and customer notified."
python -m supportpilot.cli show --ticket TCK-0001
python -m supportpilot.cli events --ticket TCK-0001

# Inspect or filter tickets
python -m supportpilot.cli list
python -m supportpilot.cli list --status Resolved
```

Ticket IDs depend on the selected database. Run `list` to find the correct ID before continuing. The global `--db` option must appear before the subcommand, for example `python -m supportpilot.cli --db data/demo.db list`.

## Workflow and human control

```text
Intake -> New -> Classified -> In Review -> Assigned -> Resolved
                  |              |            |           |
             rules suggest   human starts  human confirms resolver records
                             review         category/team  outcome
```

Classification and routing create suggestions only. The `assigned_team`, `final_category` and `final_priority` fields are saved only after a human starts review and confirms assignment. An ambiguous ticket cannot be assigned with `Unknown/Needs Review`; the reviewer must choose a valid category. Only `Assigned` tickets can be resolved, and `Resolved` is terminal.

## Classification, routing and fallback

- Category scoring uses weighted keywords. Subject matches count twice as much as message matches.
- The winning category must reach the minimum score and lead the runner-up by the configured margin.
- Unmatched, weak or ambiguous category evidence produces `Unknown/Needs Review`.
- Priority uses the highest matching urgency signal; if no signal matches, Medium is the default.
- A classifier exception uses the safe Unknown fallback and creates a `CLASSIFIER_FALLBACK` event.
- Category-to-team mapping is documented in [`docs/DAY3_ROUTING_REVIEW.md`](docs/DAY3_ROUTING_REVIEW.md).
- No LLM is called at runtime. The deterministic rule baseline works offline. A future optional model must return validated structured output and retain the same fallback and human approval gates.

Detailed rules and thresholds: [`docs/DAY2_RULES.md`](docs/DAY2_RULES.md). Final implementation notes and limitations: [`docs/DAY5_FINAL_HANDOVER.md`](docs/DAY5_FINAL_HANDOVER.md).

## Project structure

```text
supportpilot/
├── supportpilot/       # models, validation, classifier, routing, storage, CLI, API
├── data/               # fictional sample tickets and classifier test set
├── docs/               # design notes, rule docs, workflow diagram, handover
├── evidence/           # test outputs and demo logs/screenshots
├── scripts/            # reproducible Day 5 demo
├── tests/              # intake, classifier, review, API and Day 4 tests
├── streamlit_app.py    # optional intake-only Streamlit form
├── requirements.txt    # optional Streamlit dependency
└── README.md
```

## Tests and evidence

Run all automated tests:

```bash
python -m unittest discover -s tests -v
```

Tests cover valid/invalid intake, classifier rules and fallback, category/team routing, human approval, invalid/duplicate transitions, duplicate ticket rejection, resolution, and HTTP validation/duplicate responses. See [`evidence/DAY5_EVIDENCE_README.md`](evidence/DAY5_EVIDENCE_README.md) for the final evidence index.

## Optional interfaces

- **HTTP intake:** `python -m supportpilot.api --port 8000` then POST JSON to `/tickets` (see `docs/DAY1_DESIGN.md`).
- **Streamlit intake form:** install optional requirements using `python -m pip install -r requirements.txt`, then run `python -m streamlit run streamlit_app.py`. This is an intake form, not the complete review interface; use the CLI for review, assignment, resolution and audit history.

## Known limitations

Keyword matching is English-only and does not understand negation, sarcasm, paraphrases or spelling variations. The small labeled set was used while tuning rules, so its score is not independent production accuracy. Reviewer/resolver names are audit labels, not authenticated accounts. Duplicate detection is exact after case and outer-whitespace normalization, not semantic. The HTTP server is a demonstration endpoint without production authentication, rate limiting or deployment hardening. SQLite and row-count IDs are suitable for a local demo, not multi-user production scale. All included customer data is fictional.

## Responsible AI and attribution

AI assistance was used for explanations, debugging support and drafting parts of the implementation/documentation. The project owner should run, review and understand all submitted work and be ready to explain its design decisions. No external AI model is used at runtime. Do not commit real customer information, passwords, API keys or other secrets.

## Final handover

The final submission should include the accessible GitHub repository, original source, sample data, README/process notes, workflow diagram, test evidence and a narrated screen recording. Follow [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) to record the required walkthrough. Submit the repository link and viewable video through the official Friday Google Form; these external submissions must be completed by the intern.

## Full Streamlit browser dashboard (local laptop)

The Streamlit interface now supports the complete ticket workflow while reusing
the same `TicketStore`, SQLite database, classifier, validation rules, status
transitions, and audit events as the CLI.

From the project root (the folder containing `streamlit_app.py`):

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser. Use the sidebar to navigate:

1. **Overview** — ticket counts and recent activity.
2. **New Ticket** — submit a ticket; classification runs automatically.
3. **Classification Queue** — inspect suggestions and start human review.
4. **Review & Assignment** — approve or change category, priority, and team.
5. **Assigned Tickets** — enter a resolution note and resolve an assigned ticket.
6. **Resolved Tickets** — inspect completed tickets.
7. **Audit History** — review recorded workflow events.

Enter the reviewer/resolver name where requested. The classifier produces
suggestions only; a human must confirm the assignment. `Unknown/Needs Review`
cannot be selected as a final category and must be resolved by a human.

The browser dashboard and CLI share the default database at `data/tickets.db`.
Stop the local server with `Ctrl+C` in the terminal. This is a local demo setup,
not a production multi-user deployment.
