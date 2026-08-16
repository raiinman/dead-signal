"""Unified Dead Signal Data Intelligence workspace."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from dead_signal_compiler_tab import install_compiler_tab
from dead_signal_description_flow_tab import install_description_flow_tab
from dead_signal_discovery_tab import install_discovery_tab
from dead_signal_intelligence_advanced import install_advanced_tabs
from dead_signal_intelligence_window import (
    BG,
    TEXT,
    DataIntelligenceWindow,
)
from dead_signal_verification_tab import install_verification_tab


class DeadSignalDataIntelligence(DataIntelligenceWindow):
    """Complete Dead Signal research workspace over one local Miner snapshot."""

    @staticmethod
    def _tree(parent, columns, widths):
        """Build a Treeview with always-visible grab-and-drag scrollbars."""
        tree = ttk.Treeview(parent, columns=columns, show="headings", style="DSI.Treeview")
        for name, width in zip(columns, widths):
            tree.heading(name, text=name.upper())
            tree.column(name, width=width, stretch=True)

        vertical = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        return tree

    @staticmethod
    def _json_text(parent):
        """Build a text viewer with visible vertical and horizontal scrollbars."""
        text = tk.Text(
            parent,
            bg=BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=9,
            font=("Cascadia Mono", 9),
            wrap="none",
        )
        vertical = ttk.Scrollbar(parent, orient="vertical", command=text.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        return text

    def _build(self):
        super()._build()
        notebook = next(
            (child for child in self.window.winfo_children() if isinstance(child, ttk.Notebook)),
            None,
        )
        if notebook is None:
            raise RuntimeError("Dead Signal Data Intelligence notebook was not created")
        install_advanced_tabs(notebook, self)
        install_discovery_tab(notebook, self)
        install_verification_tab(notebook, self)
        install_description_flow_tab(notebook, self)
        install_compiler_tab(notebook, self)


def open_data_intelligence(parent, output: Path, open_evidence_console):
    return DeadSignalDataIntelligence(parent, output, open_evidence_console)
