"""Dead Signal Miner Windows desktop application."""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from miner_core import (
    APP_VERSION,
    MinerConfig,
    MiningCancelled,
    ROOT,
    discover_installations,
    format_exception,
    run_pipeline,
    self_test,
)
from update_manager import (
    UpdateError,
    UpdateInfo,
    check_for_updates,
    download_update,
    launch_updater,
)


BG = "#090b0d"
PANEL = "#111519"
PANEL_2 = "#171c21"
TEXT = "#eef1f4"
MUTED = "#9aa3ac"
RED = "#e52b32"
RED_DARK = "#87171c"
BORDER = "#2a3138"
SUCCESS = "#4ed083"
AMBER = "#f0a52b"
BLUE = "#3f8fcb"

PIPELINE_STAGES = (
    ("MINE", 0, 67),
    ("INDEX", 68, 76),
    ("RESOLVE", 77, 88),
    ("COMPILE", 89, 96),
    ("VERIFY", 97, 100),
)


def default_output() -> Path:
    return Path.home() / "Documents" / "Dead Signal Miner"



def settings_path() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return local / "DeadSignalMiner" / "settings.json"


def icon_path() -> Path:
    if getattr(sys, "frozen", False):
        return ROOT / "dead-signal-miner.ico"
    return ROOT.parent / "assets" / "dead-signal-miner.ico"


def update_status_path() -> Path:
    return settings_path().with_name("update-status.json")


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class DeadSignalMinerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Dead Signal Miner {APP_VERSION}")
        try:
            self.root.iconbitmap(default=str(icon_path()))
        except tk.TclError:
            pass
        self.root.geometry("1500x900")
        self.root.minsize(1180, 720)
        self.root.configure(bg=BG)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.update_worker: threading.Thread | None = None
        self.pending_update: UpdateInfo | None = None
        self.last_output = default_output()

        self.install_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(default_output()))
        self.status_var = tk.StringVar(value="Ready for a local snapshot")
        self.progress_var = tk.IntVar(value=0)
        self.workspace_var = tk.StringVar(value="Evidence Graph")
        self.activity_count = 0
        self.stage_widgets: list[dict[str, tk.Widget]] = []
        self.coverage_widgets: dict[str, tuple[tk.Label, ttk.Progressbar]] = {}

        self._configure_styles()
        self._load_settings()
        self._build_ui()
        self._report_previous_update()
        self._autodetect_install()
        self._poll_events()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("DS.Horizontal.TProgressbar", troughcolor=PANEL_2, background=RED, bordercolor=BORDER)
        style.configure("DS.TCheckbutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.map("DS.TCheckbutton", background=[("active", PANEL)], foreground=[("active", TEXT)])
        style.configure("DS.TRadiobutton", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.map("DS.TRadiobutton", background=[("active", PANEL)], foreground=[("active", TEXT)])
        style.configure(
            "Health.Horizontal.TProgressbar", troughcolor="#30353a", background=SUCCESS,
            bordercolor=PANEL, lightcolor=SUCCESS, darkcolor=SUCCESS, thickness=8,
        )
        style.configure(
            "Warning.Horizontal.TProgressbar", troughcolor="#30353a", background=AMBER,
            bordercolor=PANEL, lightcolor=AMBER, darkcolor=AMBER, thickness=8,
        )
        style.configure(
            "Activity.Treeview", background=PANEL, fieldbackground=PANEL, foreground="#cbd1d6",
            rowheight=27, borderwidth=0, font=("Segoe UI", 9),
        )
        style.configure(
            "Activity.Treeview.Heading", background=PANEL_2, foreground=TEXT,
            relief="flat", font=("Segoe UI", 9, "bold"),
        )
        style.map("Activity.Treeview", background=[("selected", RED_DARK)], foreground=[("selected", "white")])

    def _load_settings(self) -> None:
        try:
            payload = json.loads(settings_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {}
        if payload.get("install"):
            self.install_var.set(payload["install"])
        if payload.get("output"):
            self.output_var.set(payload["output"])

    def _save_settings(self) -> None:
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "install": self.install_var.get().strip(),
                    "output": self.output_var.get().strip(),
                    "mode": "full",
                    "include_artwork": True,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg=BG, padx=24, pady=14, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x")
        title_row = tk.Frame(header, bg=BG)
        title_row.pack(fill="x")
        tk.Label(title_row, text="◉", bg=BG, fg=RED, font=("Segoe UI Symbol", 23, "bold")).pack(side="left")
        tk.Label(title_row, text="DEAD SIGNAL MINER", bg=BG, fg=TEXT, font=("Bahnschrift SemiCondensed", 24, "bold")).pack(side="left", padx=(10, 22))
        tk.Label(title_row, text="Snapshot intelligence console", bg=BG, fg="#c8cdd2", font=("Segoe UI", 13)).pack(side="left", pady=(5, 0))
        self.ready_badge = tk.Label(title_row, text="  READY  ", bg="#124a26", fg="#baf7c9", font=("Segoe UI", 9, "bold"), padx=8, pady=5)
        self.ready_badge.pack(side="right")
        self.status_dot = self.ready_badge
        tk.Label(title_row, text=f"v{APP_VERSION}", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", padx=16)

        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)
        self.nav = tk.Frame(shell, bg="#0d1013", width=205, highlightbackground=BORDER, highlightthickness=1)
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)
        self.nav_buttons: dict[str, tk.Button] = {}
        for label, glyph in (("Evidence Graph", "⌁"), ("Run Pipeline", "▶"),
                             ("Explore Data", "⌕"), ("Publish & Verify", "✓")):
            button = tk.Button(
                self.nav, text=f"  {glyph}   {label}", anchor="w", command=lambda name=label: self._show_workspace(name),
                bg="#0d1013", activebackground=PANEL_2, fg="#c9ced3", activeforeground="white",
                relief="flat", bd=0, padx=18, pady=22, font=("Segoe UI", 11, "bold"), cursor="hand2",
            )
            button.pack(fill="x")
            self.nav_buttons[label] = button
        tk.Frame(self.nav, bg="#0d1013").pack(fill="both", expand=True)
        self.update_button = tk.Button(
            self.nav, text="  ↻   Check for updates", anchor="w", command=self._check_updates,
            bg="#0d1013", activebackground=PANEL_2, fg=MUTED, activeforeground=TEXT,
            relief="flat", bd=0, padx=18, pady=15, font=("Segoe UI", 9, "bold"),
        )
        self.update_button.pack(fill="x")

        self.workspace_host = tk.Frame(shell, bg=BG, padx=12, pady=12)
        self.workspace_host.pack(side="left", fill="both", expand=True)
        self.workspaces: dict[str, tk.Frame] = {}
        # Evidence Graph construction can touch a large completed snapshot.
        # Defer it until Tk has entered its event loop so the application window
        # paints immediately instead of appearing to hang during startup.
        self._build_startup_placeholder()
        self._build_run_workspace()
        self._build_explore_workspace()
        self._build_publish_workspace()
        self._show_workspace("Evidence Graph")
        self._append_log("Ready. Game files are read-only; nothing in the installation will be changed.")
        self._refresh_coverage()
        self.root.after(100, self._build_deferred_evidence_graph)

    def _build_startup_placeholder(self) -> None:
        page = self._workspace("Evidence Graph")
        panel = self._panel(page, padx=28, pady=26)
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text="EVIDENCE GRAPH", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        self._startup_status = tk.Label(
            panel, text="Preparing workspace…", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 10),
        )
        self._startup_status.pack(anchor="w", pady=(8, 0))

    def _build_deferred_evidence_graph(self) -> None:
        page = self.workspaces.get("Evidence Graph")
        if page is None or getattr(self, "_evidence_graph_ready", False):
            return
        for child in page.winfo_children():
            child.destroy()
        try:
            self._build_evidence_graph_workspace()
            self._evidence_graph_ready = True
            self._show_workspace("Evidence Graph")
        except Exception as error:
            fallback = self._panel(page, padx=28, pady=26)
            fallback.pack(fill="both", expand=True)
            tk.Label(fallback, text="EVIDENCE GRAPH", bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 22, "bold")).pack(anchor="w")
            tk.Label(fallback, text=f"Workspace unavailable: {error}", bg=PANEL, fg=AMBER,
                     font=("Segoe UI", 10), wraplength=900, justify="left").pack(anchor="w", pady=(8, 0))

    def _panel(self, parent: tk.Widget, **kwargs) -> tk.Frame:
        return tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, **kwargs)

    def _button(self, parent: tk.Widget, text: str, command, *, primary: bool = False) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command, bg=RED if primary else PANEL_2,
            activebackground="#ff4047" if primary else BORDER, fg="white" if primary else TEXT,
            activeforeground="white", relief="flat", bd=0, padx=17, pady=10,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        )

    def _workspace(self, name: str) -> tk.Frame:
        frame = tk.Frame(self.workspace_host, bg=BG)
        self.workspaces[name] = frame
        return frame

    def _show_workspace(self, name: str) -> None:
        self.workspace_var.set(name)
        for frame in self.workspaces.values():
            frame.pack_forget()
        self.workspaces[name].pack(fill="both", expand=True)
        for label, button in self.nav_buttons.items():
            button.configure(bg=PANEL_2 if label == name else "#0d1013", fg="white" if label == name else "#c9ced3")
        if name == "Publish & Verify":
            self._refresh_coverage()

    def _build_evidence_graph_workspace(self) -> None:
        """Make exact evidence analysis the Miner's primary product surface."""
        page = self._workspace("Evidence Graph")
        output = Path(self.output_var.get().strip() or default_output()).expanduser().resolve()
        try:
            from dead_signal_trace_workspace import install_weapon_identity_trace  # pylint: disable=import-outside-toplevel
            self.identity_trace = install_weapon_identity_trace(page, output, self)
        except Exception as error:
            fallback = self._panel(page, padx=28, pady=26)
            fallback.pack(fill="both", expand=True)
            tk.Label(fallback, text="EVIDENCE GRAPH", bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 22, "bold")).pack(anchor="w")
            tk.Label(fallback, text="Complete one local snapshot before tracing player-facing claims.",
                     bg=PANEL, fg=MUTED, font=("Segoe UI", 11)).pack(anchor="w", pady=(5, 18))
            tk.Label(fallback, text=str(error), bg=PANEL, fg=AMBER, justify="left",
                     wraplength=800, font=("Cascadia Mono", 9)).pack(anchor="w")
            self._button(fallback, "OPEN RUN PIPELINE", lambda: self._show_workspace("Run Pipeline"),
                         primary=True).pack(anchor="w", pady=(22, 0))

    def _build_run_workspace(self) -> None:
        page = self._workspace("Run Pipeline")
        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True)
        main = tk.Frame(body, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        health = self._panel(body, width=330, padx=18, pady=16)
        health.pack(side="right", fill="y", padx=(12, 0))
        health.pack_propagate(False)

        pipeline = self._panel(main, padx=20, pady=16)
        pipeline.pack(fill="x")
        tk.Label(pipeline, text="Run Pipeline", bg=PANEL, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(pipeline, text="Execute the full local pipeline from installed snapshot to verified site.", bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 14))
        stages = tk.Frame(pipeline, bg=PANEL)
        stages.pack(fill="x", pady=(0, 13))
        for index, (name, _low, _high) in enumerate(PIPELINE_STAGES, 1):
            card = tk.Frame(stages, bg=PANEL)
            card.pack(side="left", fill="x", expand=True)
            badge = tk.Label(card, text=str(index), bg=PANEL_2, fg=TEXT, width=2, pady=5, font=("Segoe UI", 10, "bold"))
            badge.pack(side="left")
            label = tk.Label(card, text=name.title(), bg=PANEL, fg="#cbd0d5", font=("Segoe UI", 10, "bold"))
            label.pack(side="left", padx=7)
            if index < len(PIPELINE_STAGES):
                tk.Label(card, text="━━━━", bg=PANEL, fg=BORDER).pack(side="right", padx=5)
            self.stage_widgets.append({"badge": badge, "label": label})

        paths = tk.Frame(pipeline, bg=PANEL)
        paths.pack(fill="x")
        self._path_row(paths, 0, "SOURCE INSTALL", self.install_var, self._browse_install)
        self._path_row(paths, 1, "OUTPUT DIRECTORY", self.output_var, self._browse_output)
        actions = tk.Frame(pipeline, bg=PANEL)
        actions.pack(fill="x", pady=(14, 0))
        self.start_button = self._button(actions, "▶  RUN COMPLETE PIPELINE", self._start, primary=True)
        self.start_button.pack(side="left")
        self.changed_button = self._button(actions, "↻  RUN CHANGED STAGES", self._run_changed_stages)
        self.changed_button.pack(side="left", padx=8)
        self.cancel_button = self._button(actions, "◷  STOP AFTER CURRENT STEP", self._cancel)
        self.cancel_button.configure(state="disabled")
        self.cancel_button.pack(side="left")

        summary = self._panel(main, padx=17, pady=12)
        summary.pack(fill="x", pady=(10, 0))
        tk.Label(summary, text="LAST COMPLETED RUN", bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.summary_row = tk.Frame(summary, bg=PANEL)
        self.summary_row.pack(fill="x", pady=(9, 0))
        self.summary_vars = []
        for label in ("tables", "bytecode files", "typed edges", "tests passed"):
            cell = tk.Frame(self.summary_row, bg=PANEL)
            cell.pack(side="left", fill="x", expand=True)
            value = tk.StringVar(value="—")
            self.summary_vars.append(value)
            tk.Label(cell, textvariable=value, bg=PANEL, fg=TEXT, font=("Segoe UI", 15, "bold")).pack()
            tk.Label(cell, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack()

        activity = self._panel(main, padx=0, pady=0)
        activity.pack(fill="both", expand=True, pady=(10, 0))
        activity_header = tk.Frame(activity, bg=PANEL, padx=14, pady=10)
        activity_header.pack(fill="x")
        tk.Label(activity_header, text="Pipeline Activity", bg=PANEL, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(side="left")
        self.percent_label = tk.Label(activity_header, text="0%", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.percent_label.pack(side="right")
        tk.Label(activity_header, textvariable=self.status_var, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", padx=12)
        ttk.Progressbar(activity, variable=self.progress_var, maximum=100, style="DS.Horizontal.TProgressbar").pack(fill="x")
        columns = ("time", "stage", "event", "cache")
        self.activity_table = ttk.Treeview(activity, columns=columns, show="headings", style="Activity.Treeview", height=7)
        for column, title, width in (("time", "Time", 80), ("stage", "Stage", 90), ("event", "Event", 520), ("cache", "State", 100)):
            self.activity_table.heading(column, text=title)
            self.activity_table.column(column, width=width, anchor="w", stretch=column == "event")
        self.activity_table.pack(fill="both", expand=True)
        self.log_text = tk.Text(activity, height=1, state="disabled")

        self._build_health_panel(health)

    def _build_health_panel(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Evidence Health", bg=PANEL, fg=TEXT, font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 14))
        for label, key in (("Weapons", "weapons"), ("Descriptions", "descriptions"), ("Gun stats", "gun_stats"), ("Projectile semantics", "projectile_semantics"), ("Cradle", "cradle")):
            row = tk.Frame(parent, bg=PANEL)
            row.pack(fill="x", pady=(0, 13))
            tk.Label(row, text=label, bg=PANEL, fg=TEXT, font=("Segoe UI", 10)).pack(side="left")
            count = tk.Label(row, text="—", bg=PANEL, fg=TEXT, font=("Segoe UI", 10))
            count.pack(side="right")
            bar = ttk.Progressbar(parent, maximum=100, style="Health.Horizontal.TProgressbar")
            bar.pack(fill="x", pady=(0, 13))
            self.coverage_widgets[key] = (count, bar)
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=8)
        blockers = tk.Frame(parent, bg=PANEL)
        blockers.pack(fill="x", pady=8)
        tk.Label(blockers, text="Publication blockers", bg=PANEL, fg=TEXT).pack(side="left")
        self.blocker_label = tk.Label(blockers, text="—", bg=PANEL, fg=SUCCESS, font=("Segoe UI", 12, "bold"))
        self.blocker_label.pack(side="right")
        unresolved = tk.Frame(parent, bg=PANEL)
        unresolved.pack(fill="x", pady=8)
        tk.Label(unresolved, text="Unresolved evidence", bg=PANEL, fg=TEXT).pack(side="left")
        self.unresolved_label = tk.Label(unresolved, text="—", bg=PANEL, fg=AMBER, font=("Segoe UI", 12, "bold"))
        self.unresolved_label.pack(side="right")

    def _build_explore_workspace(self) -> None:
        page = self._workspace("Explore Data")
        header = self._panel(page, padx=22, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="Explore Data", bg=PANEL, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(header, text="Search records, inspect typed relationships, and trace exact evidence from one workspace.", bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))
        cards = tk.Frame(page, bg=BG)
        cards.pack(fill="both", expand=True, pady=(12, 0))
        items = (
            ("Data Intelligence", "Browse tables, records, fields, launch coverage, and the compiler.", self._open_data_intelligence),
            ("Research Console", "Search weapons and inspect exact, typed, and unresolved evidence.", self._open_research_console),
            ("Published Dataset", "Open the current normalized website-ready records.", lambda: open_folder(Path(self.output_var.get()).expanduser() / "published" / "data")),
        )
        for title, copy, command in items:
            card = self._panel(cards, padx=22, pady=22)
            card.pack(side="left", fill="both", expand=True, padx=(0, 10))
            tk.Label(card, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 15, "bold")).pack(anchor="w")
            tk.Label(card, text=copy, bg=PANEL, fg=MUTED, justify="left", wraplength=270, font=("Segoe UI", 10)).pack(anchor="w", pady=(9, 20))
            self._button(card, "OPEN WORKSPACE", command, primary=title == "Data Intelligence").pack(anchor="w")
        self.research_button = self.nav_buttons["Explore Data"]

    def _build_publish_workspace(self) -> None:
        page = self._workspace("Publish & Verify")
        header = self._panel(page, padx=22, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="Publish & Verify", bg=PANEL, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(header, text="Review publication readiness, inspect semantic changes, and open verified output.", bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))
        toolbar = tk.Frame(page, bg=BG, pady=12)
        toolbar.pack(fill="x")
        self.open_button = self._button(toolbar, "↗  OPEN PUBLISHED SITE", lambda: open_folder(Path(self.output_var.get()).expanduser() / "published" / "site"), primary=True)
        self.open_button.pack(side="left")
        self._button(toolbar, "≠  VIEW SITE DELTA", self._open_site_delta).pack(side="left", padx=8)
        self._button(toolbar, "⇩  EXPORT EVIDENCE", self._open_evidence).pack(side="left")
        self._button(toolbar, "↻  REFRESH HEALTH", self._refresh_coverage).pack(side="right")
        self.publish_detail = tk.Text(page, bg=PANEL, fg="#cbd1d6", insertbackground=TEXT, relief="flat", bd=0, padx=18, pady=16, font=("Cascadia Mono", 10), state="disabled")
        self.publish_detail.pack(fill="both", expand=True)

    def _open_data_intelligence(self) -> None:
        try:
            from dead_signal_intelligence_hub import open_data_intelligence  # pylint: disable=import-outside-toplevel
            open_data_intelligence(
                self.root,
                Path(self.output_var.get().strip()).expanduser().resolve(),
                lambda *_args: self._open_research_console(),
            )
        except Exception as error:
            messagebox.showerror("Data Intelligence", f"A completed local snapshot is required.\n\n{error}", parent=self.root)

    def _run_changed_stages(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        output = Path(self.output_var.get().strip()).expanduser().resolve()
        if not (output / "last-run.json").is_file():
            messagebox.showinfo("Run Changed Stages", "Complete one mining run before compiling changed stages.", parent=self.root)
            return
        self.last_output = output
        self.cancel_event.clear()
        self.progress_var.set(60)
        self._set_running_state("Compiling changed intelligence stages")
        self._append_log("Changed-stage run started; unchanged heavy stages may be reused from cache.")

        def worker() -> None:
            try:
                from dead_signal_intelligence_compiler import compile_intelligence  # pylint: disable=import-outside-toplevel
                result = compile_intelligence(
                    output,
                    log=lambda value: self.events.put(("log", value)),
                    activity=lambda value: self.events.put(("log", value)),
                    progress=lambda value, label: self.events.put(("progress", (60 + int(value * .39), label))),
                )
                if self.cancel_event.is_set():
                    raise MiningCancelled("Stopped safely after intelligence compilation.")
                self.events.put(("progress", (99, "Verifying publication integrity")))
                verification = self_test()
                if not verification.get("ok"):
                    raise RuntimeError("Miner self-test failed after compilation")
                self.events.put(("complete", {"intelligence": result, "verification": verification, "changed_only": True}))
            except MiningCancelled as error:
                self.events.put(("cancelled", str(error)))
            except Exception as error:
                self.events.put(("error", (str(error), format_exception(error))))

        self.worker = threading.Thread(target=worker, name="dead-signal-changed-stages", daemon=True)
        self.worker.start()

    def _open_site_delta(self) -> None:
        path = Path(self.output_var.get()).expanduser() / "published" / "site" / "site-delta.json"
        if path.is_file():
            open_folder(path.parent)
        else:
            messagebox.showinfo("Site Delta", "Run the pipeline first to produce a site delta.", parent=self.root)

    def _open_evidence(self) -> None:
        open_folder(Path(self.output_var.get()).expanduser() / "published" / "reports")

    def _set_running_state(self, status: str) -> None:
        self.status_var.set(status)
        self.ready_badge.configure(text="  RUNNING  ", bg=RED_DARK, fg="white")
        self.start_button.configure(state="disabled", bg=RED_DARK)
        self.changed_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.update_button.configure(state="disabled")

    def _set_stage(self, progress: int) -> None:
        active = 0
        for index, (_name, low, high) in enumerate(PIPELINE_STAGES):
            if progress >= low:
                active = index
            widgets = self.stage_widgets[index]
            complete = progress > high or progress == 100
            current = low <= progress <= high
            color = SUCCESS if complete else RED if current else PANEL_2
            widgets["badge"].configure(bg=color, fg="white" if complete or current else TEXT)
            widgets["label"].configure(fg="white" if index <= active else MUTED)

    @staticmethod
    def _load_json(path: Path) -> dict:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _refresh_coverage(self) -> None:
        output = Path(self.output_var.get().strip() or default_output()).expanduser()
        reports = output / "published" / "reports"
        coverage = self._load_json(reports / "dead-signal-coverage-dashboard.json")
        fields = {str(row.get("field")): row for row in coverage.get("fields", []) if isinstance(row, dict)}
        mapping = {
            "weapons": "Weapons",
            "descriptions": "Descriptions",
            "gun_stats": "Tier-I ranged gun stats",
            "projectile_semantics": "Projectile semantics",
            "cradle": "Cradle compatibility",
        }
        for key, field in mapping.items():
            row = fields.get(field, {})
            resolved = int(row.get("resolved") or 0)
            applicable = int(row.get("applicable") or 0)
            label, bar = self.coverage_widgets[key]
            label.configure(text=str(row.get("display") or "—"))
            bar.configure(value=(resolved * 100 / applicable) if applicable else 0,
                          style="Warning.Horizontal.TProgressbar" if key == "projectile_semantics" else "Health.Horizontal.TProgressbar")
        diagnostics = self._load_json(reports / "dead-signal-self-diagnostics.json")
        record_counts = diagnostics.get("record_counts") or {}
        blockers = int(record_counts.get("blocking_findings") or record_counts.get("blockers") or 0)
        special = fields.get("Special Skill", {}).get("states") or {}
        unresolved = int(special.get("unresolved evidence state") or 0) + int(special.get("unresolved") or 0)
        self.blocker_label.configure(text=str(blockers))
        self.unresolved_label.configure(text=str(unresolved))

        registry = self._load_json(reports / "table-registry-summary.json").get("record_counts") or {}
        consumer = self._load_json(reports / "consumer-index-summary.json").get("record_counts") or {}
        graph = self._load_json(reports / "reference-graph-summary.json").get("record_counts") or {}
        values = (
            registry.get("tables") or registry.get("table_files") or "—",
            consumer.get("files") or consumer.get("pyc_files") or "—",
            graph.get("edges") or graph.get("reference_edges") or "—",
            "verified" if coverage else "—",
        )
        for variable, value in zip(self.summary_vars, values):
            variable.set(f"{value:,}" if isinstance(value, int) else str(value))
        if hasattr(self, "publish_detail"):
            lines = ["PUBLICATION READINESS", ""]
            for field in mapping.values():
                row = fields.get(field, {})
                lines.append(f"{field:<28} {row.get('display', '—')}")
            lines.extend(("", f"Publication blockers         {blockers}", f"Unresolved skill evidence    {unresolved}"))
            self.publish_detail.configure(state="normal")
            self.publish_detail.delete("1.0", "end")
            self.publish_detail.insert("end", "\n".join(lines))
            self.publish_detail.configure(state="disabled")

    def _report_previous_update(self) -> None:
        path = update_status_path()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if payload.get("status") == "complete":
            self._append_log(f"Update installed successfully. This is Dead Signal Miner v{APP_VERSION}.")
        elif payload.get("status") == "failed":
            self._append_log(f"The previous update could not be installed: {payload.get('error', 'unknown error')}")
        try:
            path.unlink()
        except OSError:
            pass

    def _path_row(self, parent: tk.Widget, row: int, label: str, variable: tk.StringVar, command) -> None:
        tk.Label(parent, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"), width=24, anchor="w").grid(row=row, column=0, sticky="w", pady=5)
        entry = tk.Entry(parent, textvariable=variable, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat", highlightbackground=BORDER, highlightcolor=RED_DARK, highlightthickness=1, font=("Segoe UI", 10))
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=5, ipady=7)
        tk.Button(parent, text="BROWSE", command=command, bg=PANEL_2, activebackground=BORDER, fg=TEXT, activeforeground=TEXT, relief="flat", bd=0, padx=14, pady=7, font=("Segoe UI", 8, "bold")).grid(row=row, column=2, sticky="e", pady=5)
        parent.grid_columnconfigure(1, weight=1)

    def _autodetect_install(self) -> None:
        if self.install_var.get().strip() and Path(self.install_var.get()).exists():
            return
        found = discover_installations()
        if found:
            self.install_var.set(str(found[0]))
            self._append_log(f"Detected Once Human: {found[0]}")

    def _browse_install(self) -> None:
        value = filedialog.askdirectory(title="Select the Once Human installation folder", initialdir=self.install_var.get() or None)
        if value:
            self.install_var.set(value)

    def _browse_output(self) -> None:
        value = filedialog.askdirectory(title="Select where miner snapshots should be stored", initialdir=self.output_var.get() or None)
        if value:
            self.output_var.set(value)

    def _open_research_console(self) -> None:
        try:
            from research_window import open_research_console  # pylint: disable=import-outside-toplevel

            output = Path(self.output_var.get().strip()).expanduser().resolve()
            open_research_console(self.root, output)
        except Exception as error:
            messagebox.showerror(
                "Research Console",
                f"A completed local snapshot is required.\n\n{error}",
                parent=self.root,
            )


    def _append_log(self, message: str) -> None:
        clean = message.strip()
        if not clean:
            return
        self.activity_count += 1
        progress = int(self.progress_var.get())
        stage = next((name for name, low, high in PIPELINE_STAGES if low <= progress <= high), "SYSTEM")
        self.activity_table.insert("", 0, values=(datetime.now().strftime("%H:%M:%S"), stage, clean, "local"))
        children = self.activity_table.get_children()
        if len(children) > 100:
            self.activity_table.delete(*children[100:])

    def _make_config(self) -> MinerConfig:
        install_text = self.install_var.get().strip()
        output_text = self.output_var.get().strip()
        if not install_text or not output_text:
            raise ValueError("Select both the Once Human folder and the miner data folder.")
        return MinerConfig(
            install=Path(install_text),
            output=Path(output_text),
            mode="full",
            include_artwork=True,
        )

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if self.update_worker and self.update_worker.is_alive():
            messagebox.showinfo("Dead Signal Miner", "Please wait for the update check to finish.", parent=self.root)
            return
        try:
            config = self._make_config().normalized()
            self._save_settings()
        except Exception as error:
            messagebox.showerror("Dead Signal Miner", str(error), parent=self.root)
            return
        self.last_output = config.output
        self.cancel_event.clear()
        self.progress_var.set(0)
        self.percent_label.configure(text="0%")
        self._set_stage(0)
        self._set_running_state("Starting complete local pipeline")
        self._append_log("\n=== NEW MINING RUN ===")

        def worker() -> None:
            try:
                mining = run_pipeline(
                    config,
                    log=lambda value: self.events.put(("log", value)),
                    progress=lambda value, label: self.events.put(("progress", (int(value * .60), label))),
                    cancel=self.cancel_event,
                )
                if self.cancel_event.is_set():
                    raise MiningCancelled("Stopped safely before intelligence compilation.")
                from dead_signal_intelligence_compiler import compile_intelligence  # pylint: disable=import-outside-toplevel
                intelligence = compile_intelligence(
                    config.output,
                    log=lambda value: self.events.put(("log", value)),
                    activity=lambda value: self.events.put(("log", value)),
                    progress=lambda value, label: self.events.put(("progress", (60 + int(value * .36), label))),
                )
                self.events.put(("progress", (97, "Verifying publication integrity")))
                verification = self_test()
                if not verification.get("ok"):
                    raise RuntimeError("Miner self-test failed after compilation")
                self.events.put(("complete", {"mining": mining, "intelligence": intelligence, "verification": verification}))
            except MiningCancelled as error:
                self.events.put(("cancelled", str(error)))
            except Exception as error:  # Keep full diagnostics in the local log.
                self.events.put(("error", (str(error), format_exception(error))))

        self.worker = threading.Thread(target=worker, name="dead-signal-miner", daemon=True)
        self.worker.start()

    def _cancel(self) -> None:
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status_var.set("Stopping after the current safe step")
        self._append_log("Stop requested. The current file will finish safely first.")

    def _set_idle_buttons(self) -> None:
        self.worker = None
        self.start_button.configure(state="normal", bg=RED)
        if hasattr(self, "changed_button"):
            self.changed_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.update_button.configure(state="normal")

    def _check_updates(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Dead Signal Miner", "Finish or stop the current mining run before updating.", parent=self.root)
            return
        if self.update_worker and self.update_worker.is_alive():
            return
        self.update_button.configure(state="disabled")
        self.start_button.configure(state="disabled", bg=RED_DARK)
        self.status_var.set("Checking for a Miner update")
        self.status_dot.configure(fg=RED)
        self._append_log(f"Checking GitHub for a version newer than v{APP_VERSION}...")

        def worker() -> None:
            try:
                self.events.put(("update_check", check_for_updates(APP_VERSION)))
            except Exception as error:
                self.events.put(("update_error", str(error)))

        self.update_worker = threading.Thread(target=worker, name="dead-signal-update-check", daemon=True)
        self.update_worker.start()

    def _offer_update(self, info: UpdateInfo) -> None:
        self.pending_update = info
        if not info.update_available:
            self.status_var.set(f"Dead Signal Miner v{APP_VERSION} is up to date")
            self.status_dot.configure(fg=SUCCESS)
            self._append_log("No newer Miner release is available.")
            self._set_idle_buttons()
            messagebox.showinfo("Dead Signal Miner", f"You already have the newest version: v{APP_VERSION}", parent=self.root)
            return
        if not info.installable:
            self.status_var.set(f"Version {info.latest_version} is being prepared")
            self.status_dot.configure(fg=MUTED)
            self._append_log(f"v{info.latest_version} is listed, but its verified Windows package is not published yet.")
            self._set_idle_buttons()
            messagebox.showinfo(
                "Dead Signal Miner",
                f"Version {info.latest_version} is being prepared, but the Windows download is not ready yet.",
                parent=self.root,
            )
            return
        if not getattr(sys, "frozen", False):
            self.status_var.set(f"Version {info.latest_version} is available")
            self.status_dot.configure(fg=SUCCESS)
            self._append_log("The development copy does not replace itself. Packaged Miner installations update in place.")
            self._set_idle_buttons()
            return
        if not messagebox.askyesno(
            "Dead Signal Miner Update",
            f"Version {info.latest_version} is available.\n\nDownload and install it now?",
            parent=self.root,
        ):
            self.status_var.set("Update postponed")
            self.status_dot.configure(fg=MUTED)
            self._set_idle_buttons()
            return
        self._download_update(info)

    def _download_update(self, info: UpdateInfo) -> None:
        self.status_var.set(f"Downloading Miner v{info.latest_version}")
        self.progress_var.set(0)
        self.percent_label.configure(text="0%")

        def worker() -> None:
            try:
                package = download_update(
                    info,
                    settings_path().parent / "updates",
                    progress=lambda received, total: self.events.put(
                        ("update_progress", (received, total, info.latest_version))
                    ),
                )
                self.events.put(("update_ready", (info, package)))
            except Exception as error:
                self.events.put(("update_error", str(error)))

        self.update_worker = threading.Thread(target=worker, name="dead-signal-update-download", daemon=True)
        self.update_worker.start()

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "log":
                    self._append_log(str(payload))
                elif event == "progress":
                    value, label = payload  # type: ignore[misc]
                    self.progress_var.set(int(value))
                    self.percent_label.configure(text=f"{int(value)}%")
                    self.status_var.set(str(label))
                    self._set_stage(int(value))
                elif event == "complete":
                    self.progress_var.set(100)
                    self.percent_label.configure(text="100%")
                    self._set_stage(100)
                    self.status_var.set("Pipeline complete — verified local output ready")
                    self.ready_badge.configure(text="  READY  ", bg="#124a26", fg="#baf7c9")
                    self._set_idle_buttons()
                    self._refresh_coverage()
                    messagebox.showinfo("Dead Signal Miner", f"Pipeline complete.\n\nVerified files are ready in:\n{self.last_output / 'published'}", parent=self.root)
                elif event == "cancelled":
                    self.status_var.set("Stopped safely")
                    self.ready_badge.configure(text="  STOPPED  ", bg=PANEL_2, fg=MUTED)
                    self._append_log(str(payload))
                    self._set_idle_buttons()
                elif event == "error":
                    short, details = payload  # type: ignore[misc]
                    self.status_var.set("Mining stopped — see the log")
                    self.ready_badge.configure(text="  ERROR  ", bg=RED_DARK, fg="white")
                    self._append_log(str(details))
                    self._set_idle_buttons()
                    messagebox.showerror("Dead Signal Miner", str(short), parent=self.root)
                elif event == "update_check":
                    self._offer_update(payload)  # type: ignore[arg-type]
                elif event == "update_progress":
                    received, total, version = payload  # type: ignore[misc]
                    percent = min(100, int(received * 100 / total))
                    self.progress_var.set(percent)
                    self.percent_label.configure(text=f"{percent}%")
                    self.status_var.set(f"Downloading Miner v{version}")
                elif event == "update_ready":
                    info, package = payload  # type: ignore[misc]
                    try:
                        if not info.sha256:
                            raise UpdateError("The verified update hash is missing")
                        launch_updater(package, info.sha256)
                    except Exception as error:
                        self.events.put(("update_error", str(error)))
                    else:
                        self.progress_var.set(100)
                        self.percent_label.configure(text="100%")
                        self._append_log("Update verified. Closing the Miner so the updater can replace it safely.")
                        messagebox.showinfo(
                            "Dead Signal Miner Update",
                            "The update is verified and ready. The Miner will close, install it, and reopen automatically.",
                            parent=self.root,
                        )
                        self._save_settings()
                        self.root.destroy()
                        return
                elif event == "update_error":
                    self.status_var.set("Update check stopped — your Miner was not changed")
                    self.status_dot.configure(fg=RED)
                    self._append_log(f"Update error: {payload}")
                    self._set_idle_buttons()
                    messagebox.showerror("Dead Signal Miner Update", str(payload), parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _on_close(self) -> None:
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("Dead Signal Miner", "Mining is still running. Close the app anyway?", parent=self.root):
                return
            self.cancel_event.set()
        self._save_settings()
        self.root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dead Signal local Once Human miner")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run", action="store_true", help="Run without opening the GUI")
    parser.add_argument("--install", type=Path)
    parser.add_argument("--output", type=Path, default=default_output())
    parser.add_argument("--mode", choices=("full",), default="full")
    return parser.parse_args()


def _safe_console_write(value: object) -> None:
    """Write diagnostics only when the current process actually has a console."""
    stream = sys.__stdout__ or sys.stdout
    if stream is None:
        return
    try:
        stream.write(str(value) + "\n")
        stream.flush()
    except (AttributeError, OSError, ValueError):
        return


def main() -> int:
    args = parse_args()
    if args.self_test:
        result = self_test()
        _safe_console_write(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    if args.run:
        installations = discover_installations()
        install = args.install or (installations[0] if installations else None)
        if not install:
            raise SystemExit("Once Human was not found; pass --install PATH")
        log_path = args.output.expanduser().resolve() / "headless-run.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        def cli_write(value: object) -> None:
            line = str(value)
            with log_path.open("a", encoding="utf-8") as destination:
                destination.write(line + "\n")
            _safe_console_write(line)

        try:
            manifest = run_pipeline(
                MinerConfig(
                    install=install,
                    output=args.output,
                    mode=args.mode,
                    include_artwork=True,
                ),
                # Extractor stdout is redirected through the log callback. Write
                # to the original stream to avoid feeding it back into itself.
                log=cli_write,
                progress=lambda value, label: cli_write(f"[{value:3d}%] {label}"),
            )
            cli_write(json.dumps(manifest, indent=2))
            return 0
        except Exception:
            cli_write(traceback.format_exc())
            return 1

    root = tk.Tk()
    DeadSignalMinerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
