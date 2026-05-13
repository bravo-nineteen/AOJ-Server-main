import ast
from pathlib import Path
import re
import unittest


def _load_intent_symbols() -> tuple:
    source_path = Path(__file__).resolve().parents[1] / "app" / "services" / "ai_chat_service.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    selected_nodes = []
    needed_assigns = {
        "_INTENT_ROUTE_PATTERNS",
        "_INTENT_ROUTE_GUIDANCE",
    }
    needed_funcs = {
        "_detect_intent_route",
        "_build_intent_router_block",
    }

    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if needed_assigns & target_names:
                selected_nodes.append(node)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in needed_assigns:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in needed_funcs:
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    compiled = compile(module, filename=str(source_path), mode="exec")
    namespace = {"re": re}
    exec(compiled, namespace)

    return namespace["_detect_intent_route"], namespace["_build_intent_router_block"]


_detect_intent_route, _build_intent_router_block = _load_intent_symbols()


class TestAIIntentRouting(unittest.TestCase):
    def test_operations_control_route(self) -> None:
        self.assertEqual(
            _detect_intent_route("Please start mission bravo now"),
            "operations_control",
        )

    def test_diagnostics_route(self) -> None:
        self.assertEqual(
            _detect_intent_route("Can you troubleshoot this offline prop issue?"),
            "diagnostics",
        )

    def test_compliance_safety_route(self) -> None:
        self.assertEqual(
            _detect_intent_route("Is this allowed for under-18 players without waiver?"),
            "compliance_safety",
        )

    def test_roster_identity_route(self) -> None:
        self.assertEqual(
            _detect_intent_route("Correction: player Kilo moved to Blue team"),
            "roster_identity",
        )

    def test_planning_rules_route(self) -> None:
        self.assertEqual(
            _detect_intent_route("Draft a briefing and schedule for domination mode"),
            "planning_rules",
        )

    def test_casual_chat_route(self) -> None:
        self.assertEqual(_detect_intent_route("thanks!"), "casual_chat")

    def test_general_route_when_no_match(self) -> None:
        self.assertEqual(
            _detect_intent_route("What should I focus on this week?"),
            "general",
        )

    def test_router_block_contains_route_and_guidance(self) -> None:
        block = _build_intent_router_block("diagnostics")
        self.assertIn("[INTENT ROUTER]", block)
        self.assertIn("route=diagnostics", block)
        self.assertIn("guidance=", block)


if __name__ == "__main__":
    unittest.main()
