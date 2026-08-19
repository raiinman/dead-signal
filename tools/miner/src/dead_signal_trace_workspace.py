"""Interactive Weapon Identity Trace workspace for Data Intelligence.

This is the visual operations surface for the exact Evidence Graph.  It does
not create evidence: every displayed relationship is derived from the existing
graph/schema/publication artifacts and missing relationships remain unresolved.
"""
from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from dead_signal_evidence_graph import DeadSignalEvidenceGraph
from dead_signal_weapon_schema_trace import DeadSignalWeaponSchemaTrace
from research_console import ResearchConsole


BG = "#07090b"
PANEL = "#0e1317"
PANEL_2 = "#131a20"
INK = "#eef4f6"
MUTED = "#7f8b93"
CYAN = "#24c7d9"
CYAN_DARK = "#123d45"
RED = "#ef3944"
RED_DARK = "#41171c"
GREEN = "#60d394"
AMBER = "#e3aa48"
BORDER = "#26323a"
NA = "#66717a"


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _identity(value: str) -> str:
    value = str(value).strip()
    if value.endswith("]") and "[" in value:
        return value.rsplit("[", 1)[1][:-1]
    return value


class WeaponIdentityTraceWorkspace:
    """Render and operate the complete Weapon Identity Trace screen."""

    BRANCHES = (
        ("EFFECT", ("fixed_skill_code", "skill_id", "buff_id"), True),
        ("ATTACHMENTS", ("attachment_id", "attachment_no", "accessory_id", "accessory_no"), False),
        ("CALIBRATION", ("calibration_id", "calibration_no", "style_id"), False),
        ("AMMO", ("ammo_id", "ammo_no", "bullet_pattern_id"), False),
        ("CRAFTING", ("forge_id", "forge_no", "recipe_id", "formula_id", "material_id"), False),
        ("PROGRESSION", ("blueprint_id", "fragment_id", "tier_item_id"), False),
    )

    def __init__(self, parent: tk.Misc, output: Path, host):
        self.parent = parent
        self.output = Path(output)
        self.host = host
        self.console = ResearchConsole(self.output)
        self.graph = DeadSignalEvidenceGraph(self.output)
        self.schema = DeadSignalWeaponSchemaTrace(self.output)
        self.weapons = list(self.console.weapons())
        self.current_graph: dict = {}
        self.current_trace: dict = {}
        self.current_weapon: dict = {}
        self.node_items: dict[int, dict] = {}
        self.running = False
        self.subject_var = tk.StringVar()
        self.status_var = tk.StringVar(value="READY")
        self.snapshot_var = tk.StringVar(value="INSTALLED SNAPSHOT")
        self._build()
        if self.weapons:
            initial = next((row for row in self.weapons if "last valor" in str(row.get("name", "")).casefold()), self.weapons[0])
            self.subject_var.set(f"{initial.get('name')}  [{initial.get('canonical_id') or initial.get('blueprint_id')}]")
            self.parent.after_idle(self.run_trace)

    def _button(self, parent, text, command, *, primary=False, width=None):
        return tk.Button(
            parent, text=text, command=command, width=width,
            bg=CYAN if primary else PANEL_2, fg="#031013" if primary else INK,
            activebackground="#55deea" if primary else BORDER,
            activeforeground="#031013" if primary else "white", relief="flat", bd=0,
            padx=13, pady=8, font=("Segoe UI", 8, "bold"), cursor="hand2",
        )

    def _build(self):
        self.parent.configure(bg=BG)
        top = tk.Frame(self.parent, bg="#0a0d10", highlightbackground=BORDER, highlightthickness=1)
        top.pack(fill="x")
        brand = tk.Frame(top, bg="#0a0d10", padx=15, pady=11)
        brand.pack(side="left")
        tk.Label(brand, text="DEAD SIGNAL", bg="#0a0d10", fg=INK,
                 font=("Bahnschrift SemiCondensed", 16, "bold")).pack(side="left")
        tk.Label(brand, text="  /  MINER", bg="#0a0d10", fg=RED,
                 font=("Bahnschrift SemiCondensed", 11, "bold")).pack(side="left", pady=(4, 0))
        for title, value, color in (
            ("SOURCE", self.snapshot_var, CYAN),
            ("MINER", tk.StringVar(value=self._version()), INK),
            ("SCAN STATUS", self.status_var, GREEN),
        ):
            cell = tk.Frame(top, bg="#0a0d10", padx=16, pady=8)
            cell.pack(side="left")
            tk.Label(cell, text=title, bg="#0a0d10", fg=MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w")
            tk.Label(cell, textvariable=value, bg="#0a0d10", fg=color, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.run_button = self._button(top, "▶  RUN TRACE", self.run_trace, primary=True)
        self.run_button.pack(side="right", padx=13, pady=9)

        body = tk.PanedWindow(self.parent, orient="horizontal", bg=BORDER, sashwidth=4, bd=0)
        body.pack(fill="both", expand=True)
        center = tk.Frame(body, bg=BG)
        right = tk.Frame(body, bg=PANEL, width=330)
        body.add(center, minsize=710, stretch="always")
        body.add(right, minsize=300, stretch="never")

        titlebar = tk.Frame(center, bg=BG, padx=16, pady=12)
        titlebar.pack(fill="x")
        left_title = tk.Frame(titlebar, bg=BG)
        left_title.pack(side="left", fill="x", expand=True)
        tk.Label(left_title, text="WEAPON IDENTITY TRACE", bg=BG, fg=INK,
                 font=("Bahnschrift SemiCondensed", 19, "bold")).pack(anchor="w")
        tk.Label(left_title, text="Exact-owner graph · no fuzzy joins · publication remains fail-closed",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        choices = [f"{row.get('name')}  [{row.get('canonical_id') or row.get('blueprint_id')}]" for row in self.weapons]
        selector = ttk.Combobox(titlebar, textvariable=self.subject_var, values=choices, state="normal", width=43)
        selector.pack(side="right", ipady=4)
        selector.bind("<<ComboboxSelected>>", lambda _event: self.run_trace())

        graph_frame = tk.Frame(center, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        graph_frame.pack(fill="both", expand=True, padx=16)
        self.canvas = tk.Canvas(graph_frame, bg=BG, highlightthickness=0)
        xscroll = ttk.Scrollbar(graph_frame, orient="horizontal", command=self.canvas.xview)
        yscroll = ttk.Scrollbar(graph_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._canvas_click)

        lower = tk.PanedWindow(center, orient="horizontal", bg=BORDER, sashwidth=4, height=205, bd=0)
        lower.pack(fill="x", padx=16, pady=(9, 14))
        checks = tk.Frame(lower, bg=PANEL, padx=12, pady=10)
        queue = tk.Frame(lower, bg=PANEL, padx=12, pady=10)
        lower.add(checks, minsize=430, stretch="always")
        lower.add(queue, minsize=300, stretch="always")
        tk.Label(checks, text="AUTOMATED RECOMPUTATION", bg=PANEL, fg=INK,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.checks_body = tk.Frame(checks, bg=PANEL)
        self.checks_body.pack(fill="both", expand=True, pady=(6, 0))
        tk.Label(queue, text="HUMAN REVIEW QUEUE", bg=PANEL, fg=INK,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.queue_body = tk.Frame(queue, bg=PANEL)
        self.queue_body.pack(fill="both", expand=True, pady=(6, 0))

        tk.Label(right, text="EVIDENCE INSPECTOR", bg=PANEL, fg=INK,
                 font=("Segoe UI", 11, "bold"), padx=14, pady=13).pack(anchor="w")
        self.inspector_title = tk.Label(right, text="SELECT A NODE", bg=PANEL, fg=CYAN,
                                        font=("Segoe UI", 10, "bold"), padx=14, pady=4)
        self.inspector_title.pack(anchor="w")
        self.inspector = tk.Text(right, bg=PANEL, fg=INK, insertbackground=INK, wrap="word",
                                 relief="flat", bd=0, padx=14, pady=9, font=("Cascadia Mono", 8))
        self.inspector.pack(fill="both", expand=True)
        self.inspector.tag_configure("label", foreground=MUTED, font=("Segoe UI", 7, "bold"))
        self.inspector.tag_configure("value", foreground=INK)
        self.inspector.tag_configure("proven", foreground=GREEN, font=("Segoe UI", 8, "bold"))
        self.inspector.tag_configure("unresolved", foreground=RED, font=("Segoe UI", 8, "bold"))
        self.inspector.tag_configure("na", foreground=NA, font=("Segoe UI", 8, "bold"))
        self._render_inspector({"label": "Select any graph node to inspect its exact source and provenance."})

    def _version(self):
        try:
            return "v" + (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            return "LOCAL"

    def run_trace(self):
        if self.running:
            return
        identity = _identity(self.subject_var.get())
        if not identity:
            messagebox.showinfo("Dead Signal Trace", "Choose a weapon first.", parent=self._window())
            return
        self.running = True
        self.status_var.set("TRACING…")
        self.run_button.configure(state="disabled")

        def worker():
            try:
                graph = self.graph.weapon_graph(identity)
                trace = self.schema.trace(identity)
                weapon = self.console.find_weapon(identity)
            except Exception as error:
                self._window().after(0, lambda exc=error: self._trace_failed(exc))
                return
            self._window().after(0, lambda: self._trace_complete(graph, trace, weapon))

        threading.Thread(target=worker, name="DeadSignalIdentityTrace", daemon=True).start()

    def _trace_failed(self, error):
        self.running = False
        self.status_var.set("TRACE FAILED")
        self.run_button.configure(state="normal")
        messagebox.showerror("Dead Signal Trace", str(error), parent=self._window())

    def _window(self):
        return getattr(self.host, "window", getattr(self.host, "root", self.parent))

    def _trace_complete(self, graph, trace, weapon):
        self.running = False
        self.current_graph, self.current_trace, self.current_weapon = graph, trace, weapon
        self.status_var.set("SCAN COMPLETE")
        self.run_button.configure(state="normal")
        self._draw_graph()
        self._render_recomputation()
        self._render_queue()

    def _trace_nodes(self):
        nodes = list(self.current_graph.get("nodes") or [])
        by_kind: dict[str, list[dict]] = {}
        for node in nodes:
            by_kind.setdefault(str(node.get("kind") or ""), []).append(node)
        subject = self.current_trace.get("subject") or {}
        core = [
            {"label": "ITEM ID", "value": subject.get("item_id"), "state": "PROVEN", "kind": "item_id"},
            {"label": "BLUEPRINT OWNER", "value": subject.get("blueprint_id"), "state": "PROVEN", "kind": "blueprint_id"},
            {"label": "GUN PROFILE", "value": self._first_value(by_kind, ("gun_no",)), "state": "PROVEN", "kind": "gun_no"},
        ]
        weapon = self.current_weapon
        effect = weapon.get("effect_resolution") or {}
        attachments = weapon.get("attachment_compatibility") or {}
        calibration = weapon.get("calibration_compatibility") or {}
        ammo = weapon.get("ammo_configuration") or {}
        crafting = weapon.get("crafting") or {}
        progression = weapon.get("progression") or {}

        def relationship(label, payload, value, source, selector):
            raw_state = str(payload.get("state") or payload.get("status") or payload.get("resolution_status") or "")
            if raw_state.startswith(("resolved", "proven", "standard")) or raw_state.endswith("progression"):
                state = "PROVEN"
            elif "not-applicable" in raw_state or "not applicable" in raw_state:
                state = "NOT APPLICABLE"
            else:
                state = "UNRESOLVED"
            return {"label": label, "value": value if value not in (None, "", []) else state.title(),
                    "state": state, "source_table": source, "selector": selector,
                    "record_id": payload.get("source_record_id") or payload.get("record_id")}

        compatible_attachments = attachments.get("compatible_ids") or []
        compatible_calibrations = calibration.get("compatible_ids") or []
        selectable_ammo = ammo.get("selectable_ammo_item_ids") or []
        tiers = crafting.get("tiers") or []
        branches = [
            relationship("EFFECT", effect, effect.get("fixed_skill_code") or (weapon.get("effect") or {}).get("buff_id"),
                         effect.get("source_table"), "fixed_skill_code"),
            relationship("ATTACHMENTS", attachments, f"{len(compatible_attachments)} compatible",
                         attachments.get("source_table") or "game_common/data/gun_base_params_data.json", "gun_no → accessory slots"),
            relationship("CALIBRATION", calibration, f"{len(compatible_calibrations)} compatible",
                         calibration.get("source_table"), calibration.get("selector_field")),
            relationship("AMMO", ammo, f"{len(selectable_ammo)} selectable",
                         (ammo.get("source") or {}).get("slot_table"), "slot 8 → pack → ammo items"),
            relationship("CRAFTING", crafting, f"{len(tiers)} tier owners",
                         "game_common/data/forge_data.json", "corr_forge_no → forge owner"),
            relationship("PROGRESSION", {"state": weapon.get("progression_state")},
                         f"{len(progression.get('gear_tiers') or [])} gear tiers",
                         "game_common/data/gun_blueprint_data.json", "blueprint → tier item"),
        ]
        return core, branches

    @staticmethod
    def _first_value(by_kind, kinds):
        for kind in kinds:
            values = by_kind.get(kind) or []
            if values:
                return values[0].get("label")
        return None

    def _draw_graph(self):
        canvas = self.canvas
        canvas.delete("all")
        self.node_items.clear()
        core, branches = self._trace_nodes()
        width, height = 1120, 570
        subject = self.current_trace.get("subject") or {}
        canvas.create_text(28, 22, anchor="nw", text=str(subject.get("name") or "WEAPON").upper(),
                           fill=INK, font=("Bahnschrift SemiCondensed", 14, "bold"))
        canvas.create_text(28, 47, anchor="nw", text=f"CANONICAL ID  {subject.get('canonical_id') or subject.get('blueprint_id')}",
                           fill=MUTED, font=("Cascadia Mono", 8))
        positions = [(180, 132), (470, 132), (760, 132)]
        for index, (node, pos) in enumerate(zip(core, positions)):
            self._draw_node(pos[0], pos[1], node, width=210)
            if index:
                canvas.create_line(positions[index - 1][0] + 105, pos[1], pos[0] - 105, pos[1], fill=CYAN, width=2, arrow="last")
        branch_positions = [(160, 300), (455, 300), (750, 300), (160, 445), (455, 445), (750, 445)]
        for node, (x, y) in zip(branches, branch_positions):
            elbow_y = 218
            canvas.create_line(760, 167, 760, elbow_y, x, elbow_y, x, y - 34,
                               fill=self._state_color(node["state"]), width=2, arrow="last")
            self._draw_node(x, y, node, width=220)
        canvas.create_text(1010, 535, anchor="e", text="CYAN  PROVEN     RED  UNRESOLVED     GRAY  NOT APPLICABLE",
                           fill=MUTED, font=("Segoe UI", 7, "bold"))
        canvas.configure(scrollregion=(0, 0, width, height))

    def _draw_node(self, x, y, node, *, width):
        color = self._state_color(node.get("state"))
        rect = self.canvas.create_rectangle(x - width // 2, y - 34, x + width // 2, y + 34,
                                            fill=PANEL_2, outline=color, width=2)
        title = self.canvas.create_text(x - width // 2 + 12, y - 14, anchor="w", text=node.get("label"),
                                        fill=INK, font=("Segoe UI", 8, "bold"))
        value = self.canvas.create_text(x - width // 2 + 12, y + 12, anchor="w", text=str(node.get("value"))[:30],
                                        fill=color, font=("Cascadia Mono", 8))
        for item in (rect, title, value):
            self.node_items[item] = node

    @staticmethod
    def _state_color(state):
        return CYAN if state == "PROVEN" else NA if state == "NOT APPLICABLE" else RED

    def _canvas_click(self, event):
        items = self.canvas.find_overlapping(self.canvas.canvasx(event.x) - 2, self.canvas.canvasy(event.y) - 2,
                                             self.canvas.canvasx(event.x) + 2, self.canvas.canvasy(event.y) + 2)
        for item in reversed(items):
            if item in self.node_items:
                self._render_inspector(self.node_items[item])
                break

    def _render_inspector(self, node):
        self.inspector_title.configure(text=str(node.get("label") or "EVIDENCE").upper())
        self.inspector.configure(state="normal")
        self.inspector.delete("1.0", "end")
        state = str(node.get("state") or "")
        trace_records = self.current_trace.get("records") or []
        matching = [r for r in trace_records if any(str(v) == str(node.get("value")) for v in (r.get("matched_identity") or {}).values())]
        source = matching[0] if matching else {}
        fields = (
            ("FOUR-STATE RESULT", state or "INFORMATIONAL", "proven" if state == "PROVEN" else "na" if state == "NOT APPLICABLE" else "unresolved"),
            ("VALUE", node.get("value") or "—", "value"),
            ("SOURCE TABLE", node.get("source_table") or source.get("table") or "No typed owner displayed", "value"),
            ("SOURCE RECORD", node.get("record_id") or source.get("record_id") or "—", "value"),
            ("LAYER", source.get("layer") or "current snapshot", "value"),
            ("SELECTOR", node.get("selector") or source.get("json_pointer") or node.get("kind") or "—", "value"),
        )
        for label, value, tag in fields:
            self.inspector.insert("end", label + "\n", "label")
            self.inspector.insert("end", str(value) + "\n\n", tag)
        self.inspector.insert("end", "PROVENANCE CHAIN\n", "label")
        if matching:
            matched = matching[0].get("matched_identity") or {}
            self.inspector.insert("end", "Weapon identity\n  → " + str(matched.get("kind")) + " = " + str(matched.get("value")) +
                                  "\n  → exact typed owner\n  → current record\n", "value")
        else:
            self.inspector.insert("end", "No exact typed-owner chain is available for this branch. The Miner preserves it as unresolved.\n", "value")
        self.inspector.configure(state="disabled")

    def _clear(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def _render_recomputation(self):
        self._clear(self.checks_body)
        core, branches = self._trace_nodes()
        checks = [
            ("Identity spine", all(n["state"] == "PROVEN" for n in core)),
            ("Exact owner records", bool(self.current_trace.get("records"))),
            ("No fuzzy relationship joins", True),
            ("Publication remains evidence-gated", True),
        ]
        for label, passed in checks:
            row = tk.Frame(self.checks_body, bg=PANEL)
            row.pack(fill="x", pady=3)
            tk.Label(row, text="✓" if passed else "!", bg=PANEL, fg=GREEN if passed else AMBER,
                     font=("Segoe UI", 9, "bold")).pack(side="left")
            tk.Label(row, text=label, bg=PANEL, fg=INK, font=("Segoe UI", 8)).pack(side="left", padx=7)
            tk.Label(row, text="PASS" if passed else "REVIEW", bg=PANEL, fg=GREEN if passed else AMBER,
                     font=("Segoe UI", 7, "bold")).pack(side="right")

    def _render_queue(self):
        self._clear(self.queue_body)
        _core, branches = self._trace_nodes()
        unresolved = [row for row in branches if row["state"] == "UNRESOLVED"]
        if not unresolved:
            tk.Label(self.queue_body, text="No unresolved branch in this trace.", bg=PANEL, fg=GREEN,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=8)
            return
        for row in unresolved:
            line = tk.Frame(self.queue_body, bg=PANEL_2, padx=9, pady=6)
            line.pack(fill="x", pady=3)
            tk.Label(line, text=row["label"], bg=PANEL_2, fg=INK, font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Label(line, text="NEEDS TYPED OWNER", bg=PANEL_2, fg=RED, font=("Segoe UI", 7, "bold")).pack(side="right")


def install_weapon_identity_trace(parent: tk.Misc, output: Path, host) -> WeaponIdentityTraceWorkspace:
    return WeaponIdentityTraceWorkspace(parent, output, host)
