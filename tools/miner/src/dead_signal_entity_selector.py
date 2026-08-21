"""Search/filter controls for the generalized Evidence Graph entity registry.

This module is presentation-only. Registry aliases help users find entities but
never establish evidence edges or publication authority.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any, Callable

from dead_signal_generalized_graph import DeadSignalGeneralizedGraph


BG = "#07090b"
PANEL = "#0e1317"
PANEL_2 = "#131a20"
INK = "#eef4f6"
MUTED = "#7f8b93"
CYAN = "#24c7d9"
BORDER = "#26323a"
RED = "#ef3944"


def entity_choice_label(entity: dict[str, Any]) -> str:
    return f"{entity.get('display_name') or entity.get('canonical_id')}  [{entity.get('canonical_id')}]"


def identity_from_choice(value: object) -> str:
    text = str(value or "").strip()
    if text.endswith("]") and "[" in text:
        return text.rsplit("[", 1)[1][:-1].strip()
    return text


class RegistrySelectorModel:
    """Testable selection model over the adapter-backed entity registry.

    Registry construction is deliberately lazy. Building the complete cross-domain
    registry may touch large snapshot products, so doing it from a Tk constructor
    can prevent the application window from ever reaching ``mainloop()``.
    """

    def __init__(self, graph: DeadSignalGeneralizedGraph):
        self.graph = graph
        registry = getattr(self.graph, "registry", None)
        entity_types = getattr(registry, "entity_types", None)
        adapter_types = list(entity_types()) if callable(entity_types) else []
        self.summary: dict[str, Any] = {
            "adapter_types": adapter_types,
            "deferred": True,
        }
        self._choices: dict[str, dict[str, Any]] = {}
        self._registry_ready = False

    def _ensure_registry(self) -> None:
        if self._registry_ready:
            return
        self.summary = self.graph.rebuild_entity_registry()
        self._registry_ready = True

    def entity_types(self) -> tuple[str, ...]:
        types = tuple(self.summary.get("adapter_types") or ())
        if types:
            return types
        registry = getattr(self.graph, "registry", None)
        entity_types = getattr(registry, "entity_types", None)
        return tuple(entity_types()) if callable(entity_types) else ()

    def search(
        self,
        query: object = "",
        *,
        entity_type: str | None = None,
        unresolved_only: bool = False,
        limit: int = 250,
    ) -> list[dict[str, Any]]:
        self._ensure_registry()
        rows = self.graph.search_entities(
            query,
            entity_type=entity_type,
            unresolved_only=unresolved_only,
            limit=limit,
        )
        self._choices = {entity_choice_label(row): row for row in rows}
        return rows

    def target_for_choice(self, choice: object, *, entity_type: str | None = None) -> dict[str, Any]:
        label = str(choice or "").strip()
        row = self._choices.get(label)
        canonical_id = row.get("canonical_id") if row else identity_from_choice(label)
        resolved_type = str((row or {}).get("entity_type") or entity_type or "").strip().casefold()
        if not resolved_type or not canonical_id:
            raise KeyError("Entity selection is incomplete")
        if row is None:
            # Navigation by an already-known canonical ID does not need the browse
            # registry. The typed adapter remains the identity/proof boundary and
            # will reject an invalid target during the trace itself.
            return {"entity_type": resolved_type, "canonical_id": str(canonical_id)}
        self._ensure_registry()
        entity = self.graph.registered_entity(resolved_type, canonical_id)
        return dict(entity["graph_target"])

    def recent(self) -> list[dict[str, Any]]:
        if not self._registry_ready:
            return []
        return self.graph.recent_entities()


class EntityRegistrySelector(tk.Frame):
    """Compact Phase-3 entity type/search/filter/recent controls."""

    def __init__(
        self,
        parent: tk.Misc,
        output: Path | str,
        *,
        subject_var: tk.StringVar,
        on_select: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=BG)
        self.subject_var = subject_var
        self.on_select = on_select
        self.model = RegistrySelectorModel(DeadSignalGeneralizedGraph(output))
        types = self.model.entity_types()
        self.entity_type_var = tk.StringVar(value=types[0] if types else "")
        self.search_var = tk.StringVar()
        self.unresolved_var = tk.BooleanVar(value=False)
        self.recent_var = tk.StringVar()
        self.status_var = tk.StringVar(value="REGISTRY DEFERRED")
        self._recent_choices: dict[str, dict[str, Any]] = {}
        self._build(types)

    def _build(self, types: tuple[str, ...]) -> None:
        filters = tk.Frame(self, bg=BG)
        filters.pack(fill="x")
        tk.Label(filters, text="ENTITY TYPE", bg=BG, fg=MUTED, font=("Segoe UI", 7, "bold")).pack(side="left")
        self.type_combo = ttk.Combobox(
            filters,
            textvariable=self.entity_type_var,
            values=list(types),
            state="readonly",
            width=14,
        )
        self.type_combo.pack(side="left", padx=(7, 12), ipady=3)
        self.type_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh())

        tk.Label(filters, text="SEARCH", bg=BG, fg=MUTED, font=("Segoe UI", 7, "bold")).pack(side="left")
        search = tk.Entry(
            filters,
            textvariable=self.search_var,
            bg=PANEL_2,
            fg=INK,
            insertbackground=INK,
            relief="flat",
            width=28,
            font=("Segoe UI", 9),
        )
        search.pack(side="left", padx=(7, 7), ipady=5)
        search.bind("<Return>", lambda _event: self.refresh())
        tk.Button(
            filters,
            text="FIND",
            command=self.refresh,
            bg=PANEL_2,
            fg=INK,
            activebackground=BORDER,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            font=("Segoe UI", 7, "bold"),
        ).pack(side="left")
        tk.Checkbutton(
            filters,
            text="UNRESOLVED ONLY",
            variable=self.unresolved_var,
            command=self.refresh,
            bg=BG,
            fg=MUTED,
            activebackground=BG,
            activeforeground=INK,
            selectcolor=PANEL_2,
            font=("Segoe UI", 7, "bold"),
        ).pack(side="left", padx=(12, 0))
        tk.Label(filters, textvariable=self.status_var, bg=BG, fg=CYAN, font=("Segoe UI", 7, "bold")).pack(side="right")

        choices = tk.Frame(self, bg=BG)
        choices.pack(fill="x", pady=(7, 0))
        tk.Label(choices, text="ENTITY", bg=BG, fg=MUTED, font=("Segoe UI", 7, "bold")).pack(side="left")
        self.subject_combo = ttk.Combobox(
            choices,
            textvariable=self.subject_var,
            state="normal",
            width=47,
        )
        self.subject_combo.pack(side="left", padx=(7, 14), ipady=3)
        self.subject_combo.bind("<<ComboboxSelected>>", self._subject_selected)
        self.subject_combo.bind("<Return>", self._subject_selected)

        tk.Label(choices, text="RECENT", bg=BG, fg=MUTED, font=("Segoe UI", 7, "bold")).pack(side="left")
        self.recent_combo = ttk.Combobox(
            choices,
            textvariable=self.recent_var,
            state="readonly",
            width=31,
        )
        self.recent_combo.pack(side="left", padx=(7, 0), ipady=3)
        self.recent_combo.bind("<<ComboboxSelected>>", self._recent_selected)

    def refresh(self) -> None:
        self.status_var.set("INDEXING…")
        entity_type = self.entity_type_var.get().strip() or None
        rows = self.model.search(
            self.search_var.get(),
            entity_type=entity_type,
            unresolved_only=self.unresolved_var.get(),
        )
        labels = [entity_choice_label(row) for row in rows]
        self.subject_combo.configure(values=labels)
        self.status_var.set(f"{len(rows)} MATCHES")
        if labels and self.subject_var.get().strip() not in labels:
            self.subject_var.set(labels[0])
        elif not labels:
            self.subject_var.set("")
        self._refresh_recent()

    def set_initial(self, name_fragment: str = "last valor") -> bool:
        """Record a preferred initial search without forcing registry construction.

        Legacy callers use the boolean result to fall back to their already-loaded
        weapon list. The actual registry is built only after Tk is interactive.
        """
        self.search_var.set(str(name_fragment or ""))
        self.status_var.set("REGISTRY DEFERRED")
        return False

    def selected_target(self) -> dict[str, Any]:
        target = self.model.target_for_choice(
            self.subject_var.get(),
            entity_type=self.entity_type_var.get(),
        )
        self._refresh_recent()
        return target

    def _subject_selected(self, _event=None) -> None:
        try:
            self.selected_target()
        except (KeyError, ValueError):
            self.status_var.set("INVALID SELECTION")
            return
        self.on_select()

    def _refresh_recent(self) -> None:
        rows = self.model.recent()
        self._recent_choices = {entity_choice_label(row): row for row in rows}
        self.recent_combo.configure(values=list(self._recent_choices))
        if not rows:
            self.recent_var.set("")

    def _recent_selected(self, _event=None) -> None:
        row = self._recent_choices.get(self.recent_var.get())
        if not row:
            return
        self.entity_type_var.set(str(row.get("entity_type") or ""))
        self.search_var.set("")
        self.unresolved_var.set(False)
        self.refresh()
        self.subject_var.set(entity_choice_label(row))
        self._subject_selected()
