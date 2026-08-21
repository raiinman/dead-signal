"""Phase 13 shell installer for the Dead Signal Miner desktop UI."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path

from dead_signal_generalized_workspace import GeneralizedEvidencePanel, OverviewPanel, ReviewQueuePanel


def install_phase13_shell(app) -> None:
    """Replace weapon-centric navigation with generalized intelligence/operations surfaces."""
    output = Path(app.output_var.get().strip()).expanduser().resolve()

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
        app.generalized_evidence = GeneralizedEvidencePanel(
            evidence_page,
            output,
            on_open_review=lambda: app._show_workspace("Review Queue"),
        )
        app.generalized_evidence.pack(fill="both", expand=True)

    overview = app._workspace("Overview")
    app.generalized_overview = OverviewPanel(
        overview,
        output,
        open_graph=lambda: app._show_workspace("Evidence Graph"),
    )
    app.generalized_overview.pack(fill="both", expand=True)

    review = app._workspace("Review Queue")

    def open_entity(entity_type: str, canonical_id: str) -> None:
        app._show_workspace("Evidence Graph")
        app.generalized_evidence.set_target(entity_type, canonical_id)

    app.generalized_review = ReviewQueuePanel(review, output, open_entity)
    app.generalized_review.pack(fill="both", expand=True)

    reports = app._workspace("Reports")
    panel = app._panel(reports, padx=24, pady=22)
    panel.pack(fill="both", expand=True)
    tk.Label(panel, text="REPORTS", bg=app.PANEL if hasattr(app, "PANEL") else "#111519", fg="#eef1f4",
             font=("Segoe UI", 20, "bold")).pack(anchor="w")
    tk.Label(panel, text="Open bounded evidence, invalidation, coverage, and snapshot diagnostics.",
             bg="#111519", fg="#9aa3ac", font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 18))
    report_items = (
        ("Claim invalidation", output / "reports" / "claim-invalidation.json"),
        ("Snapshot data diff", output / "reports" / "snapshot-data-diff.json"),
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
