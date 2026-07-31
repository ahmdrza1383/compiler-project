from .ast_node import *
from .symbol_table import SymbolTable, Symbol
from .token import SourceLocation


class AutoCompleter:
    def __init__(self, symbol_table: SymbolTable, ast_root):
        self.symbol_table = symbol_table
        self.ast_root = ast_root

    def get_completions(self, source: str, line: int, col: int) -> list:
        """
        Return completion items based on cursor position
        """
        # Step 1: Determine context
        context = self._detect_context(source, line, col)

        # Step 2: Collect visible symbols
        if context["type"] == "member_access":
            # After '.' or '->'
            obj_type = context.get("obj_type")
            if obj_type:
                return self._get_member_completions(obj_type)
        else:
            # General scope completion
            return self._get_scope_completions(context.get("prefix", ""))

        return []

    def _detect_context(self, source: str, line: int, col: int) -> dict:
        """Determine what kind of completion is needed"""
        lines = source.split("\n")
        if line > len(lines):
            return {"type": "general"}

        current_line = lines[line - 1]
        prefix = current_line[:col]

        # Check for member access
        if "." in prefix or "->" in prefix:
            # Find the object expression
            obj_expr = self._find_object_expr(prefix)
            if obj_expr:
                obj_type = self._infer_object_type(obj_expr)
                return {
                    "type": "member_access",
                    "obj_expr": obj_expr,
                    "obj_type": obj_type,
                    "prefix": prefix,
                }

        # Check for scope resolution (::) - C++ only
        if "::" in prefix:
            return {"type": "scope_resolution"}

        # Check for function arguments (inside parentheses)
        if "(" in prefix and ")" not in prefix:
            return {"type": "function_args", "prefix": prefix}

        return {"type": "general", "prefix": prefix}

    def _find_object_expr(self, prefix: str) -> str:
        """Extract object expression before '.' or '->'"""
        import re

        match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*$", prefix)
        if match:
            return match.group(1)

        match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*->\s*$", prefix)
        if match:
            return match.group(1)

        return None

    def _infer_object_type(self, obj_expr: str) -> str:
        """Infer type of object expression from symbol table"""
        symbol = self.symbol_table.resolve(obj_expr)
        if symbol:
            return symbol.type
        return None

    def _get_member_completions(self, obj_type: str) -> list:
        """Get completions for member access"""
        if obj_type is None:
            return []

        # Parse type string to find struct fields
        if obj_type.startswith("struct "):
            struct_name = obj_type[7:].strip()
            # Find struct symbol
            struct_symbol = self.symbol_table.resolve_global(struct_name)
            if struct_symbol and struct_symbol.kind == "struct":
                # Find fields in struct scope
                completions = []
                # Traverse global scope to find struct scope
                for scope in self.symbol_table.global_scope.children:
                    if scope.scope_type == "struct":
                        for name, symbol in scope.symbols.items():
                            completions.append(
                                {
                                    "label": name,
                                    "kind": "field",
                                    "type": symbol.type,
                                    "detail": f"{symbol.type} {name}",
                                    "sortOrder": 0,
                                }
                            )
                return completions

        return []

    def _get_scope_completions(self, prefix: str) -> list:
        """Get completions from current scope"""
        completions = []
        current_scope = self.symbol_table.get_current_scope()

        # Collect symbols from current scope and outer scopes
        symbols = self._collect_symbols(current_scope)

        for symbol in symbols:
            if prefix and not symbol.name.startswith(prefix):
                continue

            # Determine kind
            kind = symbol.kind
            if kind == "function":
                detail = (
                    symbol.signature if symbol.signature else f"{symbol.type} function"
                )
            else:
                detail = f"{symbol.type} {symbol.name}"

            completions.append(
                {
                    "label": symbol.name,
                    "kind": kind,
                    "type": symbol.type,
                    "detail": detail,
                    "sortOrder": self._get_sort_order(kind),
                }
            )

        # Sort by sortOrder, then by name
        completions.sort(key=lambda x: (x["sortOrder"], x["label"]))
        return completions

    def _collect_symbols(self, scope):
        """Collect all symbols from scope and its parents"""
        symbols = []
        current = scope
        while current:
            for name, symbol in current.symbols.items():
                if not any(s.name == name for s in symbols):
                    symbols.append(symbol)
            current = current.parent
        return symbols

    def _get_sort_order(self, kind: str) -> int:
        """Priority order for completion items"""
        priority = {
            "local": 0,
            "parameter": 1,
            "variable": 2,
            "function": 3,
            "struct": 4,
            "field": 5,
            "type": 6,
            "global": 7,
        }
        return priority.get(kind, 10)
