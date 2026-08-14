"""Tk research console window backed by :mod:`research_console`."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from research_console import FILTERS, ResearchConsole


BG = "#090b0d"
PANEL = "#111519"
TEXT = "#eef1f4"
MUTED = "#9aa3ac"
RED = "#e52b32"
BORDER = "#2a3138"
GREEN = "#2d9b68"
AMBER = "#c58b2a"


def graph_groups(evidence: dict) -> list[dict]:
    """Collapse exact-ID nodes into clickable field families for the visual map."""
    nodes = (evidence.get("evidence_tree") or {}).get("nodes") or []
    grouped = {}
    for node in nodes:
        if not isinstance(node, dict) or node.get("kind") == "weapon":
            continue
        kind = str(node.get("kind") or "evidence")
        group = grouped.setdefault(kind, {"kind": kind, "nodes": [], "present": 0, "missing": 0})
        group["nodes"].append(node)
        if node.get("status") == "missing-link":
            group["missing"] += 1
        else:
            group["present"] += 1
    for group in grouped.values():
        group["status"] = "missing" if not group["present"] else ("mixed" if group["missing"] else "present")
    preferred = {
        "blueprint_id": 0, "item_id": 1, "prototype_id": 2, "gun_no": 3,
        "fixed_skill_code": 4, "buff_id": 5, "raw_handle": 6,
        "translation_handle": 7, "forge_id": 8,
    }
    return sorted(grouped.values(), key=lambda row: (preferred.get(row["kind"], 100), row["kind"]))


class ResearchWindow:
    def __init__(self, parent: tk.Misc, output: Path):
        self.parent = parent
        self.service = ResearchConsole(output)
        self.window = tk.Toplevel(parent)
        self.window.title("Dead Signal Miner / Research Console")
        self.window.geometry("1280x820")
        self.window.minsize(980, 680)
        self.window.configure(bg=BG)
        self.last_evidence: dict = {}
        self._build()

    @staticmethod
    def _button(parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=RED, activebackground="#ff4047",
                         fg="white", activeforeground="white", relief="flat", bd=0,
                         padx=14, pady=7, font=("Segoe UI", 9, "bold"), cursor="hand2")

    @staticmethod
    def _text(parent):
        return tk.Text(parent, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                       padx=12, pady=10, font=("Cascadia Mono", 9), wrap="word")

    def _build(self):
        header = tk.Frame(self.window, bg=BG, padx=20, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="RESEARCH CONSOLE", bg=BG, fg=TEXT,
                 font=("Bahnschrift SemiCondensed", 22, "bold")).pack(side="left")
        tk.Label(header, text="READ-ONLY SNAPSHOT WORKSTATION", bg=BG, fg=RED,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=14, pady=(8, 0))
        tk.Label(header, text="Exact evidence is authoritative. Related results are leads only.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", pady=(8, 0))

        style = ttk.Style(self.window)
        style.configure("Research.TNotebook", background=BG, borderwidth=0)
        style.configure("Research.TNotebook.Tab", background=PANEL, foreground=TEXT, padding=(12, 7))
        style.map("Research.TNotebook.Tab", background=[("selected", RED)], foreground=[("selected", "white")])
        style.configure("Research.Treeview", background=BG, fieldbackground=BG, foreground=TEXT,
                        bordercolor=BORDER, rowheight=25)
        style.configure("Research.Treeview.Heading", background="#d8d6d1", foreground="#15181b",
                        font=("Segoe UI", 9, "bold"))
        style.map("Research.Treeview", background=[("selected", RED)], foreground=[("selected", "white")])
        notebook = ttk.Notebook(self.window, style="Research.TNotebook")
        notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self._build_search(notebook)
        self._build_investigator(notebook)
        self._build_queue(notebook)
        self._build_diff(notebook)
        self._build_notes_integrity(notebook)

    def _tab(self, notebook, title):
        frame = tk.Frame(notebook, bg=PANEL, padx=14, pady=14)
        notebook.add(frame, text=title)
        return frame

    def _build_search(self, notebook):
        frame = self._tab(notebook, "Evidence Search")
        row = tk.Frame(frame, bg=PANEL)
        row.pack(fill="x")
        self.query = tk.StringVar()
        entry = tk.Entry(row, textvariable=self.query, bg=BG, fg=TEXT, insertbackground=TEXT,
                         relief="flat", highlightbackground=BORDER, highlightcolor=RED,
                         highlightthickness=1, font=("Segoe UI", 11))
        entry.pack(side="left", fill="x", expand=True, ipady=7)
        entry.bind("<Return>", lambda _event: self._search(False))
        self._button(row, "EXACT SEARCH", lambda: self._search(False)).pack(side="left", padx=(8, 0))
        related = self._button(row, "RELATED SEARCH", lambda: self._search(True))
        related.configure(bg="#4b5158")
        related.pack(side="left", padx=(8, 0))
        filters = tk.Frame(frame, bg=PANEL)
        filters.pack(fill="x", pady=8)
        self.filter_vars = {}
        for label in FILTERS:
            var = tk.BooleanVar(value=True)
            self.filter_vars[label] = var
            tk.Checkbutton(filters, text=label, variable=var, bg=PANEL, fg=TEXT,
                           activebackground=PANEL, activeforeground=TEXT, selectcolor=BG).pack(side="left", padx=(0, 12))
        tk.Label(filters, text="Related mode never establishes identity.", bg=PANEL, fg=MUTED).pack(side="right")
        columns = ("mode", "category", "source", "field", "value")
        self.results = ttk.Treeview(frame, columns=columns, show="headings", style="Research.Treeview")
        for name, width in (("mode", 90), ("category", 110), ("source", 260), ("field", 150), ("value", 420)):
            self.results.heading(name, text=name.upper())
            self.results.column(name, width=width, stretch=True)
        self.results.pack(fill="both", expand=True)
        self.results.bind("<Button-3>", self._search_menu)

    def _search(self, related):
        try:
            selected = [name for name, var in self.filter_vars.items() if var.get()]
            self.last_evidence = self.service.search(self.query.get(), selected, related=related)
            self.results.delete(*self.results.get_children())
            for row in self.last_evidence["results"]:
                self.results.insert("", "end", values=(row.get("match"), row.get("category") or "Tables",
                                    row.get("table") or row.get("source"), row.get("field"), row.get("value") or self.query.get()))
        except Exception as error:
            messagebox.showerror("Research Search", str(error), parent=self.window)

    def _search_menu(self, event):
        item = self.results.identify_row(event.y)
        if not item:
            return
        self.results.selection_set(item)
        values = self.results.item(item, "values")
        value = values[4] if len(values) > 4 else ""
        menu = tk.Menu(self.window, tearoff=False)
        menu.add_command(label="Find References (exact ID)", command=lambda: self._reverse_lookup(value))
        menu.tk_popup(event.x_root, event.y_root)

    def _reverse_lookup(self, value):
        self.query.set(value)
        self._search(False)

    def _build_investigator(self, notebook):
        frame = self._tab(notebook, "Weapon Investigator / Graph")
        row = tk.Frame(frame, bg=PANEL)
        row.pack(fill="x")
        self.weapon_var = tk.StringVar()
        choices = [f"{row.get('name')}  [{row.get('canonical_id') or row.get('blueprint_id')}]" for row in self.service.weapons()]
        box = ttk.Combobox(row, textvariable=self.weapon_var, values=choices, state="normal")
        box.pack(side="left", fill="x", expand=True, ipady=4)
        self._button(row, "INVESTIGATE", self._investigate).pack(side="left", padx=(8, 0))
        self._button(row, "EXPORT EVIDENCE", self._export).pack(side="left", padx=(8, 0))
        resolver_bar = tk.Frame(frame, bg=PANEL)
        resolver_bar.pack(fill="x", pady=(8, 0))
        tk.Label(resolver_bar, text="RESOLVERS", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 8))
        for label, command in (
            ("BASELINE CLASSIFIER", self._show_baseline_classifier),
            ("SKILL TRIANGULATOR", self._show_skill_triangulator),
            ("FAMILY DELTA", self._show_family_delta),
            ("STATIC PYC CONTEXT", self._show_pyc_context),
        ):
            button = self._button(resolver_bar, label, command)
            button.configure(bg="#343c44", padx=10, pady=5, font=("Segoe UI", 8, "bold"))
            button.pack(side="left", padx=(0, 6))
        body = tk.PanedWindow(frame, orient="horizontal", bg=BORDER, sashwidth=5)
        body.pack(fill="both", expand=True, pady=(10, 0))
        map_panel = tk.Frame(body, bg=BG)
        detail_panel = tk.Frame(body, bg=PANEL, padx=12, pady=10)
        body.add(map_panel, minsize=600, stretch="always")
        body.add(detail_panel, minsize=310, stretch="never")
        self.graph_canvas = tk.Canvas(map_panel, bg=BG, highlightthickness=0, bd=0)
        graph_scroll = tk.Scrollbar(map_panel, orient="vertical", command=self.graph_canvas.yview)
        self.graph_canvas.configure(yscrollcommand=graph_scroll.set)
        graph_scroll.pack(side="right", fill="y")
        self.graph_canvas.pack(fill="both", expand=True)
        self.graph_canvas.bind("<MouseWheel>", lambda event: self.graph_canvas.yview_scroll(int(-event.delta / 120), "units"))
        tk.Label(detail_panel, text="EVIDENCE CARD", bg=PANEL, fg=RED,
                 font=("Bahnschrift SemiCondensed", 13, "bold")).pack(anchor="w")
        tk.Label(detail_panel, text="Click the weapon or any connected ID family.", bg=PANEL,
                 fg=MUTED, font=("Segoe UI", 9), wraplength=300, justify="left").pack(anchor="w", pady=(2, 8))
        self.investigation = self._text(detail_panel)
        self.investigation.pack(fill="both", expand=True)
        self.graph_canvas.create_text(36, 36, text="Choose a Weapon, then select INVESTIGATE",
                                      fill=MUTED, anchor="nw", font=("Segoe UI", 12, "bold"))

    def _investigate(self):
        identity = self._current_weapon_identity()
        try:
            self.last_evidence = self.service.investigate_weapon(identity)
            self._draw_weapon_map(self.last_evidence)
            self._show_weapon_card()
        except Exception as error:
            messagebox.showerror("Weapon Investigator", str(error), parent=self.window)

    def _current_weapon_identity(self):
        identity = self.weapon_var.get().strip()
        if identity.endswith("]") and "[" in identity:
            identity = identity.rsplit("[", 1)[1][:-1]
        if not identity:
            raise ValueError("Choose a Weapon first")
        return identity

    def _run_resolver(self, title, operation):
        try:
            result = operation(self._current_weapon_identity())
            self.last_evidence = result
            self._set_investigation_detail(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as error:
            messagebox.showerror(title, str(error), parent=self.window)

    def _show_baseline_classifier(self):
        self._run_resolver("Baseline Classifier", self.service.classify_weapon_baseline)

    def _show_skill_triangulator(self):
        self._run_resolver("Skill Triangulator", self.service.triangulate_weapon_skill)

    def _show_family_delta(self):
        self._run_resolver("Weapon Family Delta", self.service.weapon_family_delta)

    def _show_pyc_context(self):
        try:
            weapon = self.service.find_weapon(self._current_weapon_identity())
            symbol = self.service._fixed_skill(weapon)  # Exact extracted identifier; no fuzzy lookup.
            if not symbol:
                raise ValueError("This Weapon has no exact fixed-skill ID to inspect")
            result = self.service.static_pyc_context(symbol)
            self.last_evidence = result
            self._set_investigation_detail(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as error:
            messagebox.showerror("Static PYC Context", str(error), parent=self.window)

    def _draw_weapon_map(self, evidence):
        canvas = self.graph_canvas
        canvas.delete("all")
        self.graph_groups = graph_groups(evidence)
        self.graph_hitboxes = {}
        weapon = evidence.get("weapon") or {}
        width = max(canvas.winfo_width(), 600)
        center_x = width // 2
        center_y = 160
        canvas.create_text(28, 22, anchor="nw", text="EXACT EVIDENCE MAP", fill=TEXT,
                           font=("Bahnschrift SemiCondensed", 16, "bold"))
        canvas.create_text(28, 49, anchor="nw", text="Every line is an exact mined relationship. Red cards remain unresolved.",
                           fill=MUTED, font=("Segoe UI", 9))
        legend_x = max(350, width - 325)
        for offset, color, label in ((0, GREEN, "PROVEN"), (96, AMBER, "MIXED"), (184, RED, "MISSING")):
            canvas.create_rectangle(legend_x + offset, 24, legend_x + offset + 12, 36, fill=color, outline="")
            canvas.create_text(legend_x + offset + 18, 30, text=label, fill=MUTED, anchor="w", font=("Segoe UI", 8, "bold"))

        card = (center_x - 170, center_y - 88, center_x + 170, center_y + 88)
        rarity_colors = {"Legendary": "#d79b36", "Epic": "#a45fd2", "Rare": "#4b8ed6", "Common": "#78907b"}
        rarity = str(weapon.get("rarity") or "")
        outline = rarity_colors.get(rarity, RED)
        canvas.create_rectangle(*card, fill="#171c21", outline=outline, width=3, tags=("weapon-card",))
        canvas.create_text(center_x, center_y - 49, text=str(weapon.get("name") or "UNKNOWN WEAPON").upper(),
                           fill=TEXT, font=("Bahnschrift SemiCondensed", 18, "bold"), width=300, tags=("weapon-card",))
        canvas.create_text(center_x, center_y - 15, text=f"{weapon.get('category') or 'Weapon'}  •  {rarity or 'RARITY UNKNOWN'}",
                           fill=outline, font=("Segoe UI", 9, "bold"), tags=("weapon-card",))
        canvas.create_text(center_x, center_y + 17, text=f"BLUEPRINT {weapon.get('blueprint_id') or '—'}   /   ITEM {weapon.get('item_id') or '—'}",
                           fill=MUTED, font=("Cascadia Mono", 9), tags=("weapon-card",))
        canvas.create_text(center_x, center_y + 52, text="CLICK FOR WEAPON EVIDENCE", fill=TEXT,
                           font=("Segoe UI", 8, "bold"), tags=("weapon-card",))
        canvas.tag_bind("weapon-card", "<Button-1>", lambda _event: self._show_weapon_card())
        canvas.tag_bind("weapon-card", "<Enter>", lambda _event: canvas.configure(cursor="hand2"))
        canvas.tag_bind("weapon-card", "<Leave>", lambda _event: canvas.configure(cursor=""))

        left = self.graph_groups[::2]
        right = self.graph_groups[1::2]
        for side, groups in (("left", left), ("right", right)):
            x = 32 if side == "left" else width - 262
            for index, group in enumerate(groups):
                y = 285 + index * 92
                node_center_x = x + 115
                canvas.create_line(center_x, card[3], node_center_x, y, fill="#43505b", width=2, arrow="last")
                self._draw_group_card(canvas, x, y, group, node_center_x)
        required_height = max(410, 310 + max(len(left), len(right)) * 92)
        canvas.configure(scrollregion=(0, 0, width, required_height))

    def _draw_group_card(self, canvas, x, y, group, center_x):
        colors = {"present": GREEN, "mixed": AMBER, "missing": RED}
        color = colors[group["status"]]
        tag = f"group-{len(self.graph_hitboxes)}"
        self.graph_hitboxes[tag] = group
        canvas.create_rectangle(x, y, x + 230, y + 64, fill="#13181d", outline=color, width=2, tags=(tag,))
        title = group["kind"].replace("_", " ").upper()
        canvas.create_text(x + 12, y + 13, text=title, fill=TEXT, anchor="nw",
                           font=("Segoe UI", 9, "bold"), tags=(tag,))
        count = len(group["nodes"])
        summary = f"{count} exact value{'s' if count != 1 else ''}  •  {group['present']} proven"
        if group["missing"]:
            summary += f"  •  {group['missing']} missing"
        canvas.create_text(x + 12, y + 39, text=summary, fill=color, anchor="nw",
                           font=("Segoe UI", 8, "bold"), tags=(tag,))
        canvas.create_text(x + 213, y + 31, text="›", fill=color, font=("Segoe UI", 20, "bold"), tags=(tag,))
        canvas.tag_bind(tag, "<Button-1>", lambda _event, row=group: self._show_group_card(row))
        canvas.tag_bind(tag, "<Enter>", lambda _event: canvas.configure(cursor="hand2"))
        canvas.tag_bind(tag, "<Leave>", lambda _event: canvas.configure(cursor=""))

    def _set_investigation_detail(self, text):
        self.investigation.configure(state="normal")
        self.investigation.delete("1.0", "end")
        self.investigation.insert("1.0", text)
        self.investigation.configure(state="disabled")

    def _show_weapon_card(self):
        evidence = self.last_evidence or {}
        weapon = evidence.get("weapon") or {}
        missing = evidence.get("missing_links") or []
        translation = evidence.get("translation_forensics") or {}
        lines = [
            str(weapon.get("name") or "UNKNOWN WEAPON").upper(),
            "═" * 34,
            f"Canonical ID  {weapon.get('canonical_id') or '—'}",
            f"Blueprint ID  {weapon.get('blueprint_id') or '—'}",
            f"Item ID       {weapon.get('item_id') or '—'}",
            f"Category      {weapon.get('category') or '—'}",
            "",
            f"Evidence families  {len(getattr(self, 'graph_groups', []))}",
            f"Missing links      {len(missing)}",
            f"Translation        {translation.get('publication_status') or 'no handle evidence'}",
            "",
            "IDENTITY POLICY",
            evidence.get("identity_policy") or "Exact identifiers only.",
        ]
        self._set_investigation_detail("\n".join(lines))

    def _show_group_card(self, group):
        lines = [group["kind"].replace("_", " ").upper(), "═" * 34,
                 f"Status: {group['status'].upper()}",
                 f"Exact values: {len(group['nodes'])}", ""]
        for node in group["nodes"]:
            references = node.get("references") or []
            lines.extend([f"{node.get('label')}  [{node.get('status')}]",
                          f"  Exact references: {len(references)}"])
            for reference in references[:12]:
                lines.append(f"  • {reference.get('source')} / {reference.get('table')} / {reference.get('field')}")
            if len(references) > 12:
                lines.append(f"  • … {len(references) - 12} more exact references")
            if not references:
                lines.append("  • No exact backing occurrence found; identity remains unresolved.")
            lines.append("")
        self._set_investigation_detail("\n".join(lines))

    def _build_queue(self, notebook):
        frame = self._tab(notebook, "Unresolved Queue")
        bar = tk.Frame(frame, bg=PANEL)
        bar.pack(fill="x")
        self._button(bar, "REFRESH", self._queue).pack(side="left")
        self.queue_text = self._text(frame)
        self.queue_text.pack(fill="both", expand=True, pady=(10, 0))
        self._queue()

    def _queue(self):
        self.last_evidence = self.service.unresolved_queue()
        self.queue_text.delete("1.0", "end")
        for group, rows in self.last_evidence["groups"].items():
            self.queue_text.insert("end", f"{group.upper()}  ({len(rows)})\n")
            for row in rows:
                self.queue_text.insert("end", f"  • {row.get('name') or row.get('identity')} — {row.get('status') or row.get('variants')}\n")
            self.queue_text.insert("end", "\n")

    def _build_diff(self, notebook):
        frame = self._tab(notebook, "Snapshot Diff")
        self.before = tk.StringVar()
        self.after = tk.StringVar(value=str(self.service.published))
        for label, variable in (("BEFORE SNAPSHOT/PUBLISHED", self.before), ("AFTER SNAPSHOT/PUBLISHED", self.after)):
            row = tk.Frame(frame, bg=PANEL)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, width=28, anchor="w", bg=PANEL, fg=MUTED).pack(side="left")
            tk.Entry(row, textvariable=variable, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(side="left", fill="x", expand=True, ipady=6)
            self._button(row, "BROWSE", lambda var=variable: self._browse(var)).pack(side="left", padx=(8, 0))
        self._button(frame, "COMPARE", self._diff).pack(anchor="w", pady=8)
        self.diff_text = self._text(frame)
        self.diff_text.pack(fill="both", expand=True)

    def _browse(self, variable):
        value = filedialog.askdirectory(initialdir=str(self.service.output), parent=self.window)
        if value:
            variable.set(value)

    def _diff(self):
        try:
            self.last_evidence = self.service.diff_snapshots(self.before.get(), self.after.get())
            self.diff_text.delete("1.0", "end")
            self.diff_text.insert("1.0", json.dumps(self.last_evidence, indent=2))
        except Exception as error:
            messagebox.showerror("Snapshot Diff", str(error), parent=self.window)

    def _build_notes_integrity(self, notebook):
        frame = self._tab(notebook, "Notes / Integrity")
        split = tk.PanedWindow(frame, orient="horizontal", bg=PANEL, sashwidth=5)
        split.pack(fill="both", expand=True)
        notes = tk.Frame(split, bg=PANEL)
        integrity = tk.Frame(split, bg=PANEL)
        split.add(notes, stretch="always")
        split.add(integrity, stretch="always")
        tk.Label(notes, text="RESEARCH BOOKMARK / NOTE", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.note_target = tk.StringVar()
        tk.Entry(notes, textvariable=self.note_target, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", pady=6, ipady=6)
        self.note_text = self._text(notes)
        self.note_text.pack(fill="both", expand=True)
        self._button(notes, "SAVE NOTE", self._save_note).pack(anchor="w", pady=(8, 0))
        tk.Label(integrity, text="INTEGRITY & COVERAGE", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.integrity_text = self._text(integrity)
        self.integrity_text.pack(fill="both", expand=True, pady=(6, 0))
        self.integrity_text.insert("1.0", json.dumps(self.service.integrity_dashboard(), indent=2))

    def _save_note(self):
        try:
            item = self.service.save_note(self.note_target.get(), self.note_text.get("1.0", "end"))
            messagebox.showinfo("Research Notes", f"Saved {item['id']} locally.", parent=self.window)
        except Exception as error:
            messagebox.showerror("Research Notes", str(error), parent=self.window)

    def _export(self):
        if not self.last_evidence:
            messagebox.showinfo("Evidence Export", "Run a search or investigation first.", parent=self.window)
            return
        try:
            path = self.service.export_evidence(self.last_evidence)
            messagebox.showinfo("Evidence Export", f"Saved compact research evidence to:\n{path}", parent=self.window)
        except Exception as error:
            messagebox.showerror("Evidence Export", str(error), parent=self.window)


def open_research_console(parent: tk.Misc, output: Path) -> ResearchWindow:
    return ResearchWindow(parent, output)
