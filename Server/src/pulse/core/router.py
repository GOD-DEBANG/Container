"""
src/pulse/core/router.py

Deterministic Compiled Trie Router.
Builds the routing table at application initialization without per-request regex.
Rejects duplicate and ambiguous routes at registration time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .errors import RouteNotFoundError, MethodNotAllowedError


@dataclass
class TrieNode:
    segment: str
    is_param: bool = False
    param_name: str = ""
    # Exact static children: segment -> TrieNode
    static_children: Dict[str, TrieNode] = field(default_factory=dict)
    # Parametric child
    param_child: Optional[TrieNode] = None
    # HTTP Method -> Handler
    handlers: Dict[str, Any] = field(default_factory=dict)


class CompiledRouter:
    """
    Trie-based compiled HTTP router.
    Deterministic, zero runtime regex evaluation.
    """

    def __init__(self) -> None:
        self.root = TrieNode(segment="")
        self._registered_routes: set[tuple[str, str]] = set()

    def add_route(self, method: str, path: str, handler: Any) -> None:
        """
        Register a route in the compiled trie.
        Raises ValueError on duplicate or ambiguous routes.
        """
        method = method.upper()
        clean_path = "/" + path.strip("/") if path.strip("/") else "/"

        route_key = (method, clean_path)
        if route_key in self._registered_routes:
            raise ValueError(f"Duplicate route detected: {method} {clean_path}")

        segments = [s for s in clean_path.split("/") if s]
        curr_node = self.root

        for seg in segments:
            if seg.startswith("{") and seg.endswith("}"):
                param_name = seg[1:-1]
                if not param_name:
                    raise ValueError(f"Empty parameter name in route: {path}")

                if curr_node.param_child is not None:
                    # Check for ambiguous parameter name conflict
                    if curr_node.param_child.param_name != param_name:
                        raise ValueError(
                            f"Ambiguous route pattern: conflicting parameter '{param_name}' "
                            f"with existing '{curr_node.param_child.param_name}' under segment '{curr_node.segment}'"
                        )
                else:
                    curr_node.param_child = TrieNode(
                        segment=seg,
                        is_param=True,
                        param_name=param_name,
                    )
                curr_node = curr_node.param_child
            else:
                if seg not in curr_node.static_children:
                    curr_node.static_children[seg] = TrieNode(segment=seg)
                curr_node = curr_node.static_children[seg]

        if method in curr_node.handlers:
            raise ValueError(f"Method '{method}' already registered for path: {clean_path}")

        curr_node.handlers[method] = handler
        self._registered_routes.add(route_key)

    def match(self, method: str, path: str) -> Tuple[Any, Dict[str, str]]:
        """
        Match path and method against compiled Trie.
        Returns:
            Tuple of (handler, path_params_dict)
        Raises:
            RouteNotFoundError: If path does not exist.
            MethodNotAllowedError: If path exists but method is unsupported.
        """
        method = method.upper()
        clean_path = "/" + path.strip("/") if path.strip("/") else "/"
        segments = [s for s in clean_path.split("/") if s]

        curr_node = self.root
        params: Dict[str, str] = {}

        for seg in segments:
            if seg in curr_node.static_children:
                curr_node = curr_node.static_children[seg]
            elif curr_node.param_child is not None:
                curr_node = curr_node.param_child
                params[curr_node.param_name] = seg
            else:
                raise RouteNotFoundError(f"Route not found: {clean_path}")

        if not curr_node.handlers:
            raise RouteNotFoundError(f"Route not found: {clean_path}")

        if method not in curr_node.handlers:
            allowed = list(curr_node.handlers.keys())
            raise MethodNotAllowedError(
                f"Method {method} not allowed for {clean_path}. Allowed: {allowed}",
                details={"allowed_methods": allowed},
            )

        return curr_node.handlers[method], params
