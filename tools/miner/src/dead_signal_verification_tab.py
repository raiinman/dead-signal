"""Dead Signal manual Verification tab."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from dead_signal_publication_gate import build_gate_report, candidate_key
from dead_signal_verification import ALLOWED_EVIDENCE, delete_verification, load_verifications, save_verification


PANEL = "#111519"
BG = "#090b0d"
TEXT = "#eef1f4"
MUTED = "#9aa3ac"
RED = "#e52b32"
GREEN = "#4ed083"
AMBER = "#d5a23a"


class VerificationTab:
    def __init__(self, notebook: ttk.Notebook, host):
        self.host = host
        self.output = host.output
        self.candidate_lookup = {}
        frame = host._tab(notebook, "Verification")
        top = tk.Frame(frame, bg=PANEL)
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text="MANUAL EVIDENCE REVIEW", bg=PANEL, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(top, text="ONLY EXPLICIT REVIEW CAN CREATE VERIFIED", bg=PANEL, fg=AMBER, font=("Segoe UI", 8, "bold")).pack(side="right")

        split = tk.PanedWindow(frame, orient="horizontal", bg="#2a3138", sashwidth=5)
        split.pack(fill="both", expand=True)
        editor = tk.Frame(split, bg=PANEL, padx=10, pady=10)
        registry = tk.Frame(split, bg="#171c21", padx=10, pady=10)
        split.add(editor, minsize=560, stretch="always")
        split.add(registry, minsize=480, stretch="always")

        tk.Label(editor, text="CANDIDATE", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.candidate_var = tk.StringVar()
        self.candidate_box = ttk.Combobox(editor, textvariable=self.candidate_var, state="readonly")
        self.candidate_box.pack(fill="x", pady=(4, 10), ipady=4)

        state_row = tk.Frame(editor, bg=PANEL)
        state_row.pack(fill="x", pady=(0, 10))
        tk.Label(state_row, text="REVIEW STATE", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="left")
        self.state_var = tk.StringVar(value="VERIFIED")
        ttk.Combobox(state_row, textvariable=self.state_var, values=("VERIFIED", "CONFLICT"), state="readonly", width=14).pack(side="right")

        tk.Label(editor, text="EVIDENCE TYPES", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.evidence_vars = {}
        evidence_frame = tk.Frame(editor, bg=PANEL)
        evidence_frame.pack(fill="x", pady=(4, 10))
        preferred = ("exact_identity", "independent_source", "in_game_capture", "official_client_text", "exact_fixed_skill")
        for index, name in enumerate(preferred):
            if name not in ALLOWED_EVIDENCE:
                continue
            variable = tk.BooleanVar(value=name in {"exact_identity", "independent_source"})
            self.evidence_vars[name] = variable
            tk.Checkbutton(
                evidence_frame, text=name.replace("_", " ").upper(), variable=variable,
                bg=PANEL, fg=TEXT, activebackground=PANEL, activeforeground=TEXT,
                selectcolor=BG, font=("Segoe UI", 8),
            ).grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 20), pady=2)

        tk.Label(editor, text="SOURCE / CAPTURE REFERENCE", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.source_var = tk.StringVar()
        tk.Entry(editor, textvariable=self.source_var, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", pady=(4, 10), ipady=6)

        tk.Label(editor, text="EVIDENCE NOTE", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.note = tk.Text(editor, height=8, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0, padx=8, pady=8, wrap="word")
        self.note.pack(fill="both", expand=True, pady=(4, 10))

        buttons = tk.Frame(editor, bg=PANEL)
        buttons.pack(fill="x")
        host._button(buttons, "SAVE MANUAL VERIFICATION", self._save).pack(side="left")
        host._button(buttons, "REMOVE VERIFICATION", self._delete, muted=True).pack(side="left", padx=(8, 0))
        host._button(buttons, "REFRESH", self._refresh, muted=True).pack(side="right")

        tk.Label(registry, text="VERIFICATION REGISTRY", bg="#171c21", fg=RED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.registry_text = host._json_text(registry)
        self.registry_text.pack(fill="both", expand=True, pady=(7, 0))
        self._refresh()

    def _load_candidates(self):
        path = self.output / "published" / "reports" / "dead-signal-source-finder.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            payload = {"weapons": []}
        choices = []
        self.candidate_lookup = {}
        for weapon in payload.get("weapons") or []:
            weapon_key = str(weapon.get("blueprint_id") or weapon.get("item_id") or weapon.get("name") or "")
            for candidate in weapon.get("candidates") or []:
                key = candidate_key(weapon_key, candidate)
                label = (
                    f"{weapon.get('name')}  [{key}]  {candidate.get('state')}  "
                    f"{candidate.get('table') or 'table?'} / {candidate.get('field') or 'field?'}"
                )
                choices.append(label)
                self.candidate_lookup[label] = {"key": key, "weapon": weapon, "candidate": candidate}
        self.candidate_box.configure(values=choices)
        if choices and self.candidate_var.get() not in choices:
            self.candidate_var.set(choices[0])

    def _selected(self):
        row = self.candidate_lookup.get(self.candidate_var.get())
        if not row:
            raise ValueError("Select a Source Finder candidate first")
        return row

    def _save(self):
        try:
            selected = self._selected()
            evidence = [name for name, variable in self.evidence_vars.items() if variable.get()]
            record = save_verification(
                self.output,
                selected["key"],
                state=self.state_var.get(),
                evidence=evidence,
                note=self.note.get("1.0", "end"),
                source_ref=self.source_var.get(),
            )
            build_gate_report(self.output / "published" / "reports")
            self._refresh()
            messagebox.showinfo(
                "Dead Signal Verification",
                f"Saved manual {record['state']} review for {record['key']}.\n\nThe Publication Gate report was recalculated; public data was not changed.",
                parent=self.host.window,
            )
        except Exception as error:
            messagebox.showerror("Dead Signal Verification", str(error), parent=self.host.window)

    def _delete(self):
        try:
            selected = self._selected()
            if delete_verification(self.output, selected["key"]):
                build_gate_report(self.output / "published" / "reports")
            self._refresh()
        except Exception as error:
            messagebox.showerror("Dead Signal Verification", str(error), parent=self.host.window)

    def _refresh(self):
        self._load_candidates()
        payload = load_verifications(self.output)
        self.registry_text.delete("1.0", "end")
        self.registry_text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))


def install_verification_tab(notebook: ttk.Notebook, host) -> VerificationTab:
    controller = VerificationTab(notebook, host)
    host.verification_tab = controller
    return controller
