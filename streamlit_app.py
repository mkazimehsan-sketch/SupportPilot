"""SupportPilot browser dashboard.

Run from the project root:
    python -m streamlit run streamlit_app.py

The dashboard uses the same TicketStore, SQLite database, classifier, routing,
validation, state transitions, and audit events as the CLI.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from supportpilot.models import Category, Priority, Status, TEAMS
from supportpilot.storage import (
    TicketStore,
    TicketNotFound,
    InvalidTransition,
    DuplicateTicket,
    FINAL_CATEGORIES,
    PRIORITIES,
)
from supportpilot.validation import ValidationError

st.set_page_config(
    page_title="SupportPilot | Support Operations",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Keep one store connection for the Streamlit session. It points to the same
# default SQLite file used by the CLI, so changes are shared between both.
if "supportpilot_store" not in st.session_state:
    # Streamlit reruns the script; keep this session's DB connection alive.
    st.session_state["supportpilot_store"] = TicketStore(check_same_thread=False)
store: TicketStore = st.session_state["supportpilot_store"]

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.8rem; padding-bottom: 2.5rem;}
      [data-testid="stMetric"] {background: #f7f8fa; padding: 14px 16px; border-radius: 12px;}
      .small-muted {color: #64748b; font-size: 0.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎧 SupportPilot")
st.caption("Intelligent Support Ticket Workflow · Intake · Classification · Human Review · Resolution")

PAGES = [
    "Overview",
    "New Ticket",
    "Classification Queue",
    "Review & Assignment",
    "Assigned Tickets",
    "Resolved Tickets",
    "Audit History",
]
page = st.sidebar.radio("Workspace", PAGES, index=0)
st.sidebar.text_input("Reviewer name", key="reviewer_name", placeholder="Enter your name")
st.sidebar.divider()
st.sidebar.caption("SupportPilot · Week 02")
st.sidebar.caption("Local SQLite database · CLI compatible")


def refresh():
    st.rerun()


def show_error(exc: Exception):
    if isinstance(exc, ValidationError):
        for message in exc.errors:
            st.error(message)
    else:
        st.error(str(exc))


def ticket_frame(tickets: list[dict]) -> pd.DataFrame:
    if not tickets:
        return pd.DataFrame()
    columns = [
        "ticket_id", "status", "subject", "contact_ref",
        "suggested_category", "suggested_priority", "suggested_team",
        "final_category", "final_priority", "assigned_team",
        "reviewed_by", "resolved_by", "created_at", "updated_at",
    ]
    return pd.DataFrame(tickets).reindex(columns=columns)


def status_counts(tickets: list[dict]) -> dict[str, int]:
    return {status.value: sum(t.get("status") == status.value for t in tickets)
            for status in Status}


def ticket_details(ticket: dict):
    with st.expander(f"{ticket['ticket_id']} · {ticket['subject']}", expanded=False):
        left, right = st.columns(2)
        with left:
            st.write("**Customer reference**", ticket["contact_ref"])
            st.write("**Status**", ticket["status"])
            st.write("**Created**", ticket["created_at"])
        with right:
            st.write("**Suggested category**", ticket.get("suggested_category") or "Not classified")
            st.write("**Suggested priority**", ticket.get("suggested_priority") or "Not classified")
            st.write("**Suggested team**", ticket.get("suggested_team") or "Not routed")
        st.write("**Customer message**")
        st.write(ticket["message"])
        if ticket.get("suggestion_reason"):
            st.info(f"Classification reason: {ticket['suggestion_reason']}")
        if ticket.get("assigned_team"):
            st.success(
                f"Human-approved: {ticket.get('final_category')} · "
                f"{ticket.get('final_priority')} · {ticket.get('assigned_team')}"
            )
        if ticket.get("resolution"):
            st.write("**Resolution**", ticket["resolution"])
            st.write("**Resolved by**", ticket.get("resolved_by") or "—")


all_tickets = store.list_tickets()
counts = status_counts(all_tickets)

if page == "Overview":
    st.subheader("Operations overview")
    metric_cols = st.columns(5)
    metric_cols[0].metric("Total tickets", len(all_tickets))
    metric_cols[1].metric("New", counts[Status.NEW.value])
    metric_cols[2].metric("Needs review", counts[Status.CLASSIFIED.value] + counts[Status.IN_REVIEW.value])
    metric_cols[3].metric("Assigned", counts[Status.ASSIGNED.value])
    metric_cols[4].metric("Resolved", counts[Status.RESOLVED.value])

    st.markdown("### Workflow")
    flow_cols = st.columns(5)
    flow = [
        ("1 · Intake", "New", "Customer submits a ticket"),
        ("2 · Classify", "Classified", "Rules suggest category, priority and team"),
        ("3 · Human review", "In Review", "Reviewer checks the suggestion"),
        ("4 · Assign", "Assigned", "Reviewer confirms the final values"),
        ("5 · Resolve", "Resolved", "Team records the resolution"),
    ]
    for col, (heading, state, desc) in zip(flow_cols, flow):
        with col:
            st.markdown(f"**{heading}**")
            st.metric(state, counts[state])
            st.caption(desc)

    st.markdown("### Recent tickets")
    recent = list(reversed(all_tickets[-10:]))
    if recent:
        st.dataframe(ticket_frame(recent), use_container_width=True, hide_index=True)
    else:
        st.info("No tickets yet. Open **New Ticket** to create the first one.")

elif page == "New Ticket":
    st.subheader("Create a support ticket")
    st.caption("After saving, SupportPilot automatically runs the existing rule-based classifier.")
    with st.form("new_ticket_form", clear_on_submit=True):
        subject = st.text_input("Subject", max_chars=120, placeholder="e.g. Unable to access my account")
        message = st.text_area("Message", height=150, max_chars=2000,
                               placeholder="Describe the issue in at least 10 characters...")
        contact = st.text_input("Contact reference", placeholder="CUST-1234 or customer@example.com")
        submitted = st.form_submit_button("Submit & classify ticket", type="primary", use_container_width=True)
    if submitted:
        try:
            created = store.create_ticket(subject, message, contact)
            classified = store.classify_ticket(created.ticket_id)
            st.success(
                f"Ticket {classified['ticket_id']} saved and classified. "
                f"Suggested: {classified['suggested_category']} / "
                f"{classified['suggested_priority']} / {classified['suggested_team']}."
            )
            st.info("The suggestion is not an assignment. A human reviewer must approve it.")
        except (ValidationError, DuplicateTicket, InvalidTransition) as exc:
            show_error(exc)

    new_tickets = store.list_tickets(Status.NEW.value)
    if new_tickets:
        st.markdown("### Previously saved tickets awaiting classification")
        st.dataframe(ticket_frame(new_tickets), use_container_width=True, hide_index=True)
        if st.button("Classify all remaining New tickets"):
            done, errors = 0, []
            for ticket in new_tickets:
                try:
                    store.classify_ticket(ticket["ticket_id"])
                    done += 1
                except Exception as exc:  # display per-ticket failure, do not stop the batch
                    errors.append(f"{ticket['ticket_id']}: {exc}")
            st.success(f"Classified {done} ticket(s).")
            for error in errors:
                st.error(error)
            refresh()

elif page == "Classification Queue":
    st.subheader("Classification queue")
    st.write("These tickets have system-generated suggestions and are waiting for a human decision.")
    classified = store.list_tickets(Status.CLASSIFIED.value)
    if not classified:
        st.success("No classified tickets are waiting for review.")
    for ticket in classified:
        ticket_details(ticket)
        if st.button(f"Start review · {ticket['ticket_id']}", key=f"start_{ticket['ticket_id']}"):
            reviewer = st.session_state.get("reviewer_name", "").strip()
            if not reviewer:
                st.warning("Enter your name in the Reviewer name field in the sidebar first.")
            else:
                try:
                    store.start_review(ticket["ticket_id"], reviewer)
                    st.success(f"{ticket['ticket_id']} moved to In Review.")
                    refresh()
                except (ValidationError, InvalidTransition, TicketNotFound) as exc:
                    show_error(exc)

elif page == "Review & Assignment":
    st.subheader("Human review & assignment")
    st.warning("Only the human-confirmation action below can assign a ticket. Suggestions remain non-final until confirmed.")
    reviewer = st.session_state.get("reviewer_name", "")
    in_review = store.list_tickets(Status.IN_REVIEW.value)
    if not in_review:
        st.info("No tickets are currently In Review. Start a review from the Classification Queue.")
    for ticket in in_review:
        st.markdown(f"---\n### {ticket['ticket_id']} · {ticket['subject']}")
        st.write(ticket["message"])
        if ticket.get("suggested_category") == Category.UNKNOWN.value:
            st.warning("The classifier could not determine a reliable category. Choose the correct category manually before assignment.")
        st.info(
            f"System suggestion: {ticket['suggested_category']} · "
            f"{ticket['suggested_priority']} · {ticket['suggested_team']}\n\n"
            f"Reason: {ticket['suggestion_reason']}"
        )
        suggested_cat = ticket.get("suggested_category")
        cat_index = FINAL_CATEGORIES.index(suggested_cat) if suggested_cat in FINAL_CATEGORIES else FINAL_CATEGORIES.index("General")
        suggested_pri = ticket.get("suggested_priority")
        pri_index = PRIORITIES.index(suggested_pri) if suggested_pri in PRIORITIES else 1
        suggested_team = ticket.get("suggested_team")
        team_index = TEAMS.index(suggested_team) if suggested_team in TEAMS else TEAMS.index("General Support")
        with st.form(f"assignment_{ticket['ticket_id']}"):
            category = st.selectbox("Final category", FINAL_CATEGORIES, index=cat_index,
                                    help="Unknown/Needs Review cannot be a final category.")
            priority = st.selectbox("Final priority", PRIORITIES, index=pri_index)
            team = st.selectbox("Assigned team", TEAMS, index=team_index)
            confirm = st.form_submit_button("Confirm & assign ticket", type="primary")
        if confirm:
            if not reviewer.strip():
                st.error("Reviewer name is required.")
            else:
                try:
                    updated = store.confirm_assignment(
                        ticket["ticket_id"], reviewer, category=category,
                        priority=priority, team=team
                    )
                    st.success(f"{updated['ticket_id']} assigned to {updated['assigned_team']}.")
                    refresh()
                except (ValidationError, InvalidTransition, TicketNotFound) as exc:
                    show_error(exc)

elif page == "Assigned Tickets":
    st.subheader("Assigned tickets")
    assigned = store.list_tickets(Status.ASSIGNED.value)
    if not assigned:
        st.info("No tickets are currently assigned.")
    for ticket in assigned:
        ticket_details(ticket)
        with st.form(f"resolve_{ticket['ticket_id']}"):
            resolver = st.text_input("Resolved by", key=f"resolver_{ticket['ticket_id']}", placeholder="Your name")
            resolution = st.text_area("Resolution note", key=f"resolution_{ticket['ticket_id']}",
                                      max_chars=1000, placeholder="Explain how the issue was resolved...")
            resolve = st.form_submit_button("Mark as resolved", type="primary")
        if resolve:
            try:
                updated = store.resolve_ticket(ticket["ticket_id"], resolver, resolution)
                st.success(f"{updated['ticket_id']} successfully resolved.")
                refresh()
            except (ValidationError, InvalidTransition, TicketNotFound) as exc:
                show_error(exc)

elif page == "Resolved Tickets":
    st.subheader("Resolved tickets")
    resolved = store.list_tickets(Status.RESOLVED.value)
    if resolved:
        st.dataframe(ticket_frame(resolved), use_container_width=True, hide_index=True)
        for ticket in resolved:
            ticket_details(ticket)
    else:
        st.info("No tickets have been resolved yet.")

elif page == "Audit History":
    st.subheader("Audit history")
    ticket_ids = ["All tickets"] + [t["ticket_id"] for t in all_tickets]
    selected = st.selectbox("Filter by ticket", ticket_ids)
    events = store.list_events(None if selected == "All tickets" else selected)
    if events:
        st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
    else:
        st.info("No audit events found for this selection.")

st.sidebar.divider()
st.sidebar.caption("Workflow safeguards")
st.sidebar.caption("✓ Human approval before assignment")
st.sidebar.caption("✓ Duplicate ticket protection")
st.sidebar.caption("✓ Valid state transitions")
st.sidebar.caption("✓ Audit event history")
