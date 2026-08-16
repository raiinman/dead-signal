"""Guided item schema trace tab for Dead Signal Data Intelligence."""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from dead_signal_weapon_schema_trace import DeadSignalWeaponSchemaTrace
from research_console import ResearchConsole

PANEL = "#111519"
PANEL_2 = "#171c21"
RED = "#e52b32"
AMBER = "#d5a23a"
BORDER = "#2a3138"


class SchemaTraceTab:
    def __init__(self, notebook: ttk.Notebook, host):
        self.notebook = notebook
        self.host = host
        self.console = ResearchConsole(host.output)
        self.tracer = DeadSignalWeaponSchemaTrace(host.output)
        self.choices = [
            f"{row.get('name')}  [{row.get('canonical_id') or row.get('blueprint_id')}]"
            for row in self.console.weapons()
        ]
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
        tk.Label(
            bar,
            text="IDENTITY MAP → EXACT OWNER → NEOX RECORD → TYPED NEXT ID",
            bg=PANEL, fg=AMBER, font=("Segoe UI", 8, "bold"),
        ).pack(side="right", padx=(12, 0))

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
            "Equal numbers in unrelated systems are not followed.\n",
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
