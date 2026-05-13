import ast
from pathlib import Path
import unittest


class TestSchemaExports(unittest.TestCase):
    def test_route_schema_references_are_reexported(self) -> None:
        backend_dir = Path(__file__).resolve().parents[1]
        routes_dir = backend_dir / "app" / "routes"
        schemas_init = backend_dir / "app" / "schemas" / "__init__.py"

        route_schema_refs: set[str] = set()
        for route_file in routes_dir.glob("*.py"):
            if route_file.name == "__init__.py":
                continue
            tree = ast.parse(route_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    if node.value.id == "schemas":
                        route_schema_refs.add(node.attr)

        init_tree = ast.parse(schemas_init.read_text(encoding="utf-8"))
        exported: set[str] = set()
        for node in init_tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for item in node.value.elts:
                            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                                exported.add(item.value)

        missing = sorted(route_schema_refs - exported)
        self.assertEqual(missing, [], f"Missing schema re-exports: {missing}")


if __name__ == "__main__":
    unittest.main()
