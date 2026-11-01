"""Guard Clean Architecture import boundaries with Python's standard library."""
import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"


def _module_name(path):
    relative = path.relative_to(PROJECT_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_import(module_name, node):
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level:
            package = module_name.split(".")[:-1]
            remove = node.level - 1
            if remove:
                package = package[:-remove]
            prefix = ".".join(package)
            base = ".".join(part for part in (prefix, node.module or "") if part)
        else:
            base = node.module or ""
        names = [
            ".".join(part for part in (base, alias.name) if part)
            for alias in node.names
            if alias.name != "*"
        ]
        return names or ([base] if base else [])
    return []


def _imports(path):
    module_name = _module_name(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for imported in _resolve_import(module_name, node):
                yield node.lineno, imported


def _starts_with(module, prefix):
    return module == prefix or module.startswith(prefix + ".")


class DependencyRuleTests(unittest.TestCase):
    def test_domain_does_not_depend_on_application_or_outer_adapters(self):
        forbidden = ("app.application", "app.adapters", "tkinter", "sqlite3",
                     "openpyxl", "reportlab")
        violations = []
        for path in sorted((APP_ROOT / "domain").rglob("*.py")):
            for line, imported in _imports(path):
                if any(_starts_with(imported, prefix) for prefix in forbidden):
                    violations.append("%s:%s imports %s" % (path.relative_to(PROJECT_ROOT), line, imported))
        self.assertEqual([], violations, "Domain layer must remain framework and adapter independent")

    def test_application_does_not_depend_on_outer_adapters_or_frameworks(self):
        forbidden = ("app.adapters", "tkinter", "sqlite3", "openpyxl", "reportlab")
        violations = []
        for path in sorted((APP_ROOT / "application").rglob("*.py")):
            for line, imported in _imports(path):
                if any(_starts_with(imported, prefix) for prefix in forbidden):
                    violations.append("%s:%s imports %s" % (path.relative_to(PROJECT_ROOT), line, imported))
        self.assertEqual([], violations, "Application layer must depend on ports, domain, and standard library")

    def test_adapters_do_not_import_the_composition_root(self):
        violations = []
        for path in sorted((APP_ROOT / "adapters").rglob("*.py")):
            for line, imported in _imports(path):
                if _starts_with(imported, "app.main"):
                    violations.append("%s:%s imports %s" % (path.relative_to(PROJECT_ROOT), line, imported))
        self.assertEqual([], violations, "Adapters must not depend on the composition root")

    def test_tkinter_ui_uses_application_facade_for_data_access(self):
        forbidden = (
            "app.adapters.sqlite_repository",
            "app.adapters.salak_publisher",
            "app.adapters.seed_catalog_reader",
            "app.adapters.excel_adapter",
            "app.adapters.pdf_adapter",
            "sqlite3",
            "openpyxl",
            "reportlab",
        )
        violations = []
        for path in sorted((APP_ROOT / "adapters" / "tkinter_ui").rglob("*.py")):
            for line, imported in _imports(path):
                if any(_starts_with(imported, prefix) for prefix in forbidden):
                    violations.append("%s:%s imports %s" % (path.relative_to(PROJECT_ROOT), line, imported))
        self.assertEqual([], violations,
                         "Tkinter UI must use application use cases instead of data-access adapters")


if __name__ == "__main__":
    unittest.main()
