"""
Load LangGraph ``ToolNode`` / ``InjectedState`` without importing ``langgraph.prebuilt``.

``langgraph.prebuilt``'s package ``__init__`` eagerly imports ``create_react_agent``,
which pulls ``langchain_core.language_models`` and (transitively) optional
``transformers`` / ``torch``. Some Windows installs have a broken ``torch`` DLL,
which makes the whole app fail to import. The ``tool_node`` submodule itself has
a lighter import graph, so we load it by file path.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path

logger = logging.getLogger("wasla.langgraph_tool_node")


def _load_tool_node_module() -> types.ModuleType:
    name = "wasla_langgraph_prebuilt_tool_node"
    if name in sys.modules:
        return sys.modules[name]
    import langgraph.graph as lg_graph

    root = Path(lg_graph.__file__).resolve().parent.parent
    path = root / "prebuilt" / "tool_node.py"
    if not path.is_file():
        msg = f"langgraph tool_node not found at {path}"
        raise ImportError(msg)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not create spec for langgraph tool_node")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_tool_node_exports() -> tuple[type, type]:
    """Prefer direct ``tool_node`` load (avoids eager torch/transformers on some hosts)."""
    try:
        mod = _load_tool_node_module()
        return mod.ToolNode, mod.InjectedState
    except (ImportError, OSError, FileNotFoundError) as exc:
        logger.warning(
            "Falling back to langgraph.prebuilt import (tool_node path load failed: %s)",
            exc,
        )
        from langgraph.prebuilt import InjectedState, ToolNode

        return ToolNode, InjectedState


ToolNode, InjectedState = _load_tool_node_exports()

__all__ = ["InjectedState", "ToolNode"]
