"""Phase 13 shell installer for the Dead Signal Miner desktop UI."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from dead_signal_generalized_workspace import GeneralizedEvidencePanel, OverviewPanel, ReviewQueuePanel
from dead_signal_publication_integration import PublicationIntegration


def _snapshot_fallback(parent, app, title: str) -> None:
    panel = app._panel(parent, padx=28, pady=26)
    panel.pack(fill="both", expand=True)
    tk.Label(panel, text=title, bg="#111519", fg="#eef1f4",
             font=("Segoe UI", 22, "bold")).pack(anchor="w")
    tk.Label(panel, text="Complete one local snapshot before opening generalized intelligence.",
             bg="#111519", fg="#9aa3ac", font=("Segoe UI", 11)).pack(anchor="w", pady=(5, 18))
    app._button(panel, "OPEN RUN PIPELINE", lambda: app._show_workspace("Run Pipeline"),
                primary=True).pack(anchor="w")


def install_phase13_shell(app) -> None:
    """Replace weapon-centric navigation with generalized intelligence/operations surfaces."""
    output = Path(app.output_var.get().strip()).expanduser().resolve()
    snapshot_ready = (output / "last-run.json").is_file()

    # Reuse existing operational pages under Phase-13 names.
    if "Explore Data" in app.workspaces:
        app.workspaces["Resolvers"] = app.workspaces.pop("Explore Data")
    if "Publish & Verify" in app.workspaces:
        app.workspaces["Publication"] = app.workspaces.pop("Publish & Verify")

    # Replace the old weapon-only evidence renderer with the generalized renderer.
    evidence_page = app.workspaces.get("Evidence Graph")
    if evidence_page is not None:
        for child in evidence_page.winfo_children():
            child.destroy()
        if snapshot_ready:
            app.generalized_evidence = GeneralizedEvidencePanel(
                evidence_page,
                output,
                on_open_review=lambda: app._show_workspace("Review Queue"),
            )
            app.generalized_evidence.pack(fill="both", expand=True)
        else:
            app.generalized_evidence = None
            _snapshot_fallback(evidence_page, app, "EVIDENCE GRAPH")

    overview = app._workspace("Overview")
    if snapshot_ready:
        app.generalized_overview = OverviewPanel(
            overview,
            output,
            open_graph=lambda: app._show_workspace("Evidence Graph"),
        )
        app.generalized_overview.pack(fill="both", expand=True)
    else:
        app.generalized_overview = None
        _snapshot_fallback(overview, app, "INTELLIGENCE OVERVIEW")

    review = app._workspace("Review Queue")

    def open_entity(entity_type: str, canonical_id: str) -> None:
        if app.generalized_evidence is None:
            app._show_workspace("Run Pipeline")
            return
        app._show_workspace("Evidence Graph")
        app.generalized_evidence.set_target(entity_type, canonical_id)

    if snapshot_ready:
        app.generalized_review = ReviewQueuePanel(review, output, open_entity)
        app.generalized_review.pack(fill="both", expand=True)
    else:
        app.generalized_review = None
        _snapshot_fallback(review, app, "REVIEW QUEUE")

    reports = app._workspace("Reports")
    panel = app._panel(reports, padx=24, pady=22)
    panel.pack(fill="both", expand=True)
    tk.Label(panel, text="REPORTS", bg="#111519", fg="#eef1f4",
             font=("Segoe UI", 20, "bold")).pack(anchor="w")
    tk.Label(panel, text="Open bounded evidence, invalidation, coverage, snapshot, and publication diagnostics.",
             bg="#111519", fg="#9aa3ac", font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 18))

    publication_status = tk.StringVar(value="CLAIM-BACKED PUBLICATION AUDIT READY" if (output / "published" / "reports" / "evidence-publication-contracts.json").is_file() else "AUDIT NOT BUILT")
    audit_row = tk.Frame(panel, bg="#111519")
    audit_row.pack(fill="x", pady=(0, 12))
    tk.Label(audit_row, textvariable=publication_status, bg="#111519", fg="#9aa3ac",
             font=("Segoe UI", 8, "bold")).pack(side="right")

    def build_publication_audit() -> None:
        if not snapshot_ready:
            app._show_workspace("Run Pipeline")
            return
        publication_status.set("BUILDING…")
        try:
            result = PublicationIntegration(output).build(persist=True)
        except Exception as error:
            publication_status.set("AUDIT FAILED")
            messagebox.showerror("Publication Audit", str(error), parent=app.root)
            return
        counts = result.get("record_counts") or {}
        publication_status.set(
            f"{counts.get('publishable', 0)} PUBLISHABLE / {counts.get('blocked', 0)} BLOCKED / {counts.get('omitted', 0)} OMITTED"
        )

    app._button(audit_row, "BUILD CLAIM-BACKED PUBLICATION AUDIT", build_publication_audit,
                primary=True).pack(side="left")

    report_items = (
        ("Publication contracts", output / "published" / "reports" / "evidence-publication-contracts.json"),
        ("Claim invalidation", output / "reports" / "claim-invalidation.json"),
        ("Snapshot data diff", output / "published" / "reports" / "snapshot-data-diff.json"),
        ("Published reports", output / "published" / "reports"),
        ("Research review data", output / "research"),
    )
    for label, path in report_items:
        row = tk.Frame(panel, bg="#111519"); row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg="#111519", fg="#eef1f4", width=24, anchor="w").pack(side="left")
        tk.Label(row, text=str(path), bg="#111519", fg="#9aa3ac", anchor="w").pack(side="left", fill="x", expand=True)

    # Rebuild the navigation with explicit Intelligence / Operations grouping.
    for child in list(app.nav.winfo_children()):
        child.destroy()
    app.nav_buttons = {}

    def section(text: str) -> None:
        tk.Label(app.nav, text=text, bg="#0d1013", fg="#6f7b84", anchor="w",
                 padx=18, pady=8, font=("Segoe UI", 8, "bold")).pack(fill="x")

    def nav_button(label: str, glyph: str) -> None:
        button = tk.Button(
            app.nav, text=f"  {glyph}   {label}", anchor="w",
            command=lambda name=label: app._show_workspace(name),
            bg="#0d1013", activebackground="#171c21", fg="#c9ced3", activeforeground="white",
            relief="flat", bd=0, padx=18, pady=11, font=("Segoe UI", 10, "bold"), cursor="hand2",
        )
        button.pack(fill="x")
        app.nav_buttons[label] = button

    section("INTELLIGENCE")
    nav_button("Overview", "◉")
    nav_button("Evidence Graph", "⌁")
    nav_button("Review Queue", "!")
    section("OPERATIONS")
    nav_button("Run Pipeline", "▶")
    nav_button("Resolvers", "⌕")
    nav_button("Publication", "✓")
    nav_button("Reports", "≡")
    tk.Frame(app.nav, bg="#0d1013").pack(fill="both", expand=True)
    app.update_button = tk.Button(
        app.nav, text="  ↻   Check for updates", anchor="w", command=app._check_updates,
        bg="#0d1013", activebackground="#171c21", fg="#9aa3ac", activeforeground="#eef1f4",
        relief="flat", bd=0, padx=18, pady=15, font=("Segoe UI", 9, "bold"),
    )
    app.update_button.pack(fill="x")
    app._show_workspace("Overview")
