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
        self.root.geometry("1080x760")
        self.root.minsize(900, 650)
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
        header = tk.Frame(self.root, bg=BG, padx=28, pady=20)
        header.pack(fill="x")
        title_row = tk.Frame(header, bg=BG)
        title_row.pack(fill="x")
        tk.Label(title_row, text="DEAD SIGNAL", bg=BG, fg=TEXT, font=("Bahnschrift SemiCondensed", 26, "bold")).pack(side="left")
        tk.Label(title_row, text="  /  LOCAL GAME MINER", bg=BG, fg=RED, font=("Bahnschrift SemiCondensed", 16, "bold")).pack(side="left", pady=(8, 0))
        tk.Label(title_row, text=f"v{APP_VERSION}", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", pady=(12, 0))
        tk.Label(
            header,
            text="One click turns your installed Once Human files into website-ready data. No uploads. No AI usage.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 11),
            anchor="w",
        ).pack(fill="x", pady=(5, 0))

        content = tk.Frame(self.root, bg=BG, padx=28)
        content.pack(fill="both", expand=True)
        settings = tk.Frame(content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=20, pady=16)
        settings.pack(fill="x")

        self._path_row(settings, 0, "ONCE HUMAN FOLDER", self.install_var, self._browse_install)
        self._path_row(settings, 1, "MINER DATA FOLDER", self.output_var, self._browse_output)
        options = tk.Frame(settings, bg=PANEL)
        options.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(14, 2))
        left = tk.Frame(options, bg=PANEL)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text="COMPLETE HARVEST", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(
            left,
            text="All database categories + every referenced display image",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(5, 0))
        tk.Label(
            left,
            text="Artwork is required data and is always included.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(3, 0))
        right = tk.Frame(options, bg=PANEL)
        right.pack(side="right", fill="x", expand=True, padx=(30, 0))
        tk.Label(right, text="PUBLISHING & INTEGRITY", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(
            right,
            text="Automatically builds web datasets, readiness checks, change reports, and snapshot hashes.",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 10),
            justify="left",
            wraplength=430,
        ).pack(anchor="w", pady=(5, 0))

        actions = tk.Frame(content, bg=BG, pady=15)
        actions.pack(fill="x")
        self.start_button = tk.Button(actions, text="MINE COMPLETE DATABASE", command=self._start, bg=RED, activebackground="#ff4047", fg="white", activeforeground="white", relief="flat", bd=0, padx=30, pady=12, font=("Bahnschrift SemiCondensed", 14, "bold"), cursor="hand2")
        self.start_button.pack(side="left")
        self.cancel_button = tk.Button(actions, text="STOP AFTER THIS STEP", command=self._cancel, bg=PANEL_2, activebackground=BORDER, fg=MUTED, activeforeground=TEXT, relief="flat", bd=0, padx=18, pady=12, font=("Segoe UI", 9, "bold"), state="disabled")
        self.cancel_button.pack(side="left", padx=(10, 0))
        self.open_button = tk.Button(actions, text="OPEN OUTPUT", command=lambda: open_folder(self.last_output / "published"), bg=PANEL_2, activebackground=BORDER, fg=TEXT, activeforeground=TEXT, relief="flat", bd=0, padx=18, pady=12, font=("Segoe UI", 9, "bold"))
        self.open_button.pack(side="right")
        self.research_button = tk.Button(actions, text="RESEARCH CONSOLE", command=self._open_research_console, bg=PANEL_2, activebackground=BORDER, fg=TEXT, activeforeground=TEXT, relief="flat", bd=0, padx=18, pady=12, font=("Segoe UI", 9, "bold"))
        self.research_button.pack(side="right", padx=(0, 10))
        self.update_button = tk.Button(actions, text="CHECK FOR UPDATES", command=self._check_updates, bg=PANEL_2, activebackground=BORDER, fg=TEXT, activeforeground=TEXT, relief="flat", bd=0, padx=18, pady=12, font=("Segoe UI", 9, "bold"))
        self.update_button.pack(side="right", padx=(0, 10))

        status_panel = tk.Frame(content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=14)
        status_panel.pack(fill="both", expand=True, pady=(0, 20))
        status_row = tk.Frame(status_panel, bg=PANEL)
        status_row.pack(fill="x")
        self.status_dot = tk.Label(status_row, text="●", bg=PANEL, fg=RED, font=("Segoe UI", 11))
        self.status_dot.pack(side="left")
        tk.Label(status_row, textvariable=self.status_var, bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(7, 0))
        self.percent_label = tk.Label(status_row, text="0%", bg=PANEL, fg=MUTED, font=("Segoe UI", 10, "bold"))
        self.percent_label.pack(side="right")
        ttk.Progressbar(status_panel, variable=self.progress_var, maximum=100, style="DS.Horizontal.TProgressbar").pack(fill="x", pady=(10, 13))

        log_frame = tk.Frame(status_panel, bg=BG, highlightbackground="#20262c", highlightthickness=1)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, bg=BG, fg="#c9d0d6", insertbackground=TEXT, relief="flat", bd=0, padx=12, pady=10, font=("Cascadia Mono", 9), wrap="word", state="disabled")
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=PANEL_2)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)
        self._append_log("Ready. The installed game is only read; nothing in the game folder will be changed.")

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
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

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
        self.status_var.set("Starting complete local snapshot")
        self.status_dot.configure(fg=RED)
        self.start_button.configure(state="disabled", bg=RED_DARK)
        self.cancel_button.configure(state="normal")
        self.update_button.configure(state="disabled")
        self._append_log("\n=== NEW MINING RUN ===")

        def worker() -> None:
            try:
                result = run_pipeline(
                    config,
                    log=lambda value: self.events.put(("log", value)),
                    progress=lambda value, label: self.events.put(("progress", (value, label))),
                    cancel=self.cancel_event,
                )
                self.events.put(("complete", result))
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
        self.start_button.configure(state="normal", bg=RED)
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
                elif event == "complete":
                    self.progress_var.set(100)
                    self.percent_label.configure(text="100%")
                    self.status_var.set("Complete snapshot ready — no upload was used")
                    self.status_dot.configure(fg=SUCCESS)
                    self._set_idle_buttons()
                    messagebox.showinfo("Dead Signal Miner", f"Mining complete.\n\nFiles are ready in:\n{self.last_output / 'published'}", parent=self.root)
                elif event == "cancelled":
                    self.status_var.set("Stopped safely")
                    self.status_dot.configure(fg=MUTED)
                    self._append_log(str(payload))
                    self._set_idle_buttons()
                elif event == "error":
                    short, details = payload  # type: ignore[misc]
                    self.status_var.set("Mining stopped — see the log")
                    self.status_dot.configure(fg=RED)
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


def main() -> int:
    args = parse_args()
    if args.self_test:
        result = self_test()
        print(json.dumps(result, indent=2))
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
            # sys.__stdout__ is None in the packaged windowed executable.
            if sys.__stdout__ is not None:
                sys.__stdout__.write(line + "\n")
                sys.__stdout__.flush()

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
