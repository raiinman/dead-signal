"""Guided item schema trace tab for Dead Signal Data Intelligence."""
from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from dead_signal_schema_trace_batch import DeadSignalSchemaTraceBatch
from dead_signal_weapon_schema_trace import DeadSignalWeaponSchemaTrace
from research_console import ResearchConsole

PANEL = "#111519"
PANEL_2 = "#171c21"
RED = "#e52b32"
AMBER = "#d5a23a"
BORDER = "#2a3138"
MUTED = "#9aa3ac"


class SchemaTraceTab:
    def __init__(self, notebook: ttk.Notebook, host):
        self.notebook = notebook
        self.host = host
        self.console = ResearchConsole(host.output)
        self.tracer = DeadSignalWeaponSchemaTrace(host.output)
        self.batch = DeadSignalSchemaTraceBatch(host.output)
        self.choices = [
            f"{row.get('name')}  [{row.get('canonical_id') or row.get('blueprint_id')}]"
            for row in self.console.weapons()
        ]
        self._batch_running = False
        self._build()

    @staticmethod
    def _identity(value: str) -> str:
        value = str(value).strip()
        if value.endswith("]") and "[" in value:
            return value.rsplit("[", 1)[1][:-1]
        return value

    def _build(self):
        frame = self.host._tab(self.notebook, "Schema Trace")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x", pady=(0, 8))
        self.subject_var = tk.StringVar()
        box = ttk.Combobox(bar, textvariable=self.subject_var, values=self.choices, state="normal")
        box.pack(side="left", fill="x", expand=True, ipady=4)
        self.host._button(bar, "TRACE ITEM SCHEMA", self._run).pack(side="left", padx=(8, 0))
        self.batch_button = self.host._button(bar, "TRACE ALL + EXPORT", self._start_batch, muted=True)
        self.batch_button.pack(side="left", padx=(8, 0))

        status_bar = tk.Frame(frame, bg=PANEL)
        status_bar.pack(fill="x", pady=(0, 8))
        self.batch_status = tk.StringVar(value="Ready — guided trace follows typed owner records only")
        tk.Label(status_bar, textvariable=self.batch_status, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(
            status_bar,
            text="IDENTITY MAP → EXACT OWNER → NEOX RECORD → TYPED NEXT ID",
            bg=PANEL, fg=AMBER, font=("Segoe UI", 8, "bold"),
        ).pack(side="right")

        split = tk.PanedWindow(frame, orient="horizontal", bg=BORDER, sashwidth=5)
        split.pack(fill="both", expand=True)
        left = tk.Frame(split, bg=PANEL_2)
        right = tk.Frame(split, bg=PANEL_2)
        split.add(left, minsize=650, stretch="always")
        split.add(right, minsize=430, stretch="always")
        tk.Label(left, text="GUIDED EXACT TRACE", bg=PANEL_2, fg=RED,
                 font=("Segoe UI", 9, "bold"), padx=8, pady=7).pack(anchor="w")
        self.trace_text = self.host._json_text(left)
        self.trace_text.pack(fill="both", expand=True, padx=7, pady=(0, 7))
        self.trace_text.insert(
            "1.0",
            "Choose an item and run TRACE ITEM SCHEMA.\n\n"
            "This automates the Identity Map + Exact Search + NeoX Explorer loop.\n"
            "Equal numbers in unrelated systems are not followed.\n\n"
            "TRACE ALL + EXPORT runs the same bounded logic across every published weapon\n"
            "and writes research/schema-trace-all-weapons.json.\n",
        )
        tk.Label(right, text="RAW EVIDENCE REPORT", bg=PANEL_2, fg=RED,
                 font=("Segoe UI", 9, "bold"), padx=8, pady=7).pack(anchor="w")
        self.raw_text = self.host._json_text(right)
        self.raw_text.pack(fill="both", expand=True, padx=7, pady=(0, 7))

    def _run(self):
        identity = self._identity(self.subject_var.get())
        if not identity:
            messagebox.showinfo("Dead Signal Schema Trace", "Choose an item first.", parent=self.host.window)
            return
        try:
            result = self.tracer.trace(identity)
        except Exception as error:
            messagebox.showerror("Dead Signal Schema Trace", str(error), parent=self.host.window)
            return
        self._render(result)

    def _start_batch(self):
        if self._batch_running:
            return
        self._batch_running = True
        self.batch_button.configure(state="disabled")
        self.batch_status.set("Starting full guided schema trace…")
        self.trace_text.delete("1.0", "end")
        self.trace_text.insert(
            "1.0",
            "TRACE ALL RUNNING\n\n"
            "Every published weapon is being traced through typed exact owner records.\n"
            "The UI remains responsive while the research report is built.\n",
        )

        def activity(message):
            self.host.window.after(0, lambda text=str(message): self.batch_status.set(text))

        def worker():
            try:
                result = self.batch.run(activity=activity)
            except Exception as error:
                self.host.window.after(0, lambda exc=error: self._batch_failed(exc))
                return
            self.host.window.after(0, lambda payload=result: self._batch_complete(payload))

        threading.Thread(target=worker, name="DeadSignalSchemaTraceBatch", daemon=True).start()

    def _batch_failed(self, error):
        self._batch_running = False
        self.batch_button.configure(state="normal")
        self.batch_status.set("Batch schema trace failed")
        messagebox.showerror("Dead Signal Schema Trace", str(error), parent=self.host.window)

    def _batch_complete(self, result):
        self._batch_running = False
        self.batch_button.configure(state="normal")
        counts = result.get("record_counts") or {}
        self.batch_status.set(
            f"DONE — {counts.get('weapons_traced', 0)}/{counts.get('weapons_requested', 0)} traced; "
            f"{counts.get('with_unresolved_stops', 0)} with unresolved stops"
        )
        lines = [
            "ALL-WEAPON GUIDED SCHEMA TRACE",
            "═" * 78,
            f"Weapons requested: {counts.get('weapons_requested', 0)}",
            f"Weapons traced: {counts.get('weapons_traced', 0)}",
            f"Clean traces: {counts.get('clean', 0)}",
            f"With unresolved stops: {counts.get('with_unresolved_stops', 0)}",
            f"Failures: {counts.get('failures', 0)}",
            f"Typed branches discovered: {counts.get('typed_branches', 0)}",
            f"Owner records opened: {counts.get('owner_records', 0)}",
            f"Broad equal-scalar refs skipped: {counts.get('skipped_broad_exact_references', 0)}",
            "",
            f"Report: {result.get('report_path')}",
            "",
            "UNRESOLVED WEAPONS",
        ]
        unresolved = [row for row in result.get("weapons") or [] if row.get("unresolved_stop_count")]
        for row in unresolved:
            lines.append(
                f"  {row.get('name')}  [{row.get('canonical_id')}] — "
                f"{row.get('unresolved_stop_count')} stop(s), {row.get('typed_branch_count')} typed branches"
            )
            for stop in (row.get("unresolved_stops") or [])[:8]:
                lines.append(
                    f"    └─ depth {stop.get('depth')}: {stop.get('kind')}={stop.get('value')} [{stop.get('state')}]"
                )
        if not unresolved:
            lines.append("  none")
        if result.get("failures"):
            lines.extend(["", "FAILURES"])
            for row in result.get("failures") or []:
                lines.append(f"  {row.get('name')}: {row.get('error')}")
        self.trace_text.delete("1.0", "end")
        self.trace_text.insert("1.0", "\n".join(lines))
        self.raw_text.delete("1.0", "end")
        self.raw_text.insert("1.0", json.dumps(result, ensure_ascii=False, indent=2))

    def _render(self, result):
        subject = result.get("subject") or {}
        lines = [
            str(subject.get("name") or "ITEM").upper(),
            "═" * 78,
            f"Blueprint: {subject.get('blueprint_id')}    Item: {subject.get('item_id')}    Prototype: {subject.get('prototype_id')}",
            "",
        ]
        records_by_identity = {}
        for record in result.get("records") or []:
            matched = record.get("matched_identity") or {}
            key = (matched.get("kind"), str(matched.get("value")))
            records_by_identity.setdefault(key, []).append(record)
        identities = sorted(
            result.get("identities") or [],
            key=lambda row: (int(row.get("depth") or 0), str(row.get("kind")), str(row.get("value"))),
        )
        for row in identities:
            kind, value = str(row.get("kind") or "identity"), str(row.get("value") or "")
            indent = "  " * int(row.get("depth") or 0)
            lines.append(
                f"{indent}{kind.upper()}  {value}  [{row.get('state')}]  {row.get('exact_reference_count')} exact refs"
            )
            owners = records_by_identity.get((kind, value), [])
            if not owners:
                lines.append(f"{indent}  └─ no compatible owner record followed")
            for record in owners:
                lines.append(f"{indent}  └─ {record.get('table')} / {record.get('record_id')} ({record.get('layer')})")
                for outbound in record.get("outbound_typed_identities") or []:
                    lines.append(
                        f"{indent}       → {outbound.get('field')} = {outbound.get('value')} [{outbound.get('kind')}]"
                    )
            lines.append("")
        counts = result.get("record_counts") or {}
        lines.extend([
            "SUMMARY",
            f"  identities processed: {counts.get('identities_processed')}",
            f"  exact NeoX records opened: {counts.get('records_opened')}",
            f"  broad equal-scalar refs intentionally skipped: {counts.get('skipped_broad_exact_references')}",
            "",
            "POLICY",
            str((result.get("policy") or {}).get("matching") or ""),
        ])
        self.trace_text.delete("1.0", "end")
        self.trace_text.insert("1.0", "\n".join(lines))
        self.raw_text.delete("1.0", "end")
        self.raw_text.insert("1.0", json.dumps(result, ensure_ascii=False, indent=2))


def install_schema_trace_tab(notebook: ttk.Notebook, host) -> SchemaTraceTab:
    controller = SchemaTraceTab(notebook, host)
    host.schema_trace = controller
    return controller
