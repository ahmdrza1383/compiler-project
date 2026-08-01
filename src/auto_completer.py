import re
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
        context = self._detect_context(source, line, col)

        if context["type"] == "member_access":
            obj_type = context.get("obj_type")
            if obj_type:
                return self._get_member_completions(obj_type, context.get("prefix", ""))
        elif context["type"] == "function_args":
            return self._get_function_arg_completions(context, line, col)
        else:
            return self._get_scope_completions(context.get("prefix", ""), line, col)

        return []

    def _detect_context(self, source: str, line: int, col: int) -> dict:
        lines = source.split("\n")
        if line > len(lines) or line < 1:
            return {"type": "general", "prefix": ""}

        current_line = lines[line - 1]
        text_before_cursor = current_line[:col]

        match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)$', text_before_cursor)
        typing_prefix = match.group(1) if match else ""

        member_match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\.|->)\s*([a-zA-Z0-9_]*)$", text_before_cursor)
        if member_match:
            obj_expr = member_match.group(1)
            obj_type = self._infer_object_type(obj_expr)
            return {
                "type": "member_access",
                "obj_expr": obj_expr,
                "obj_type": obj_type,
                "prefix": member_match.group(2) 
            }

        func_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*$', text_before_cursor)
        if func_match:
            func_name = func_match.group(1)
            args_str = text_before_cursor[func_match.start():]
            arg_index = args_str.count(',') 
            return {
                "type": "function_args",
                "func_name": func_name,
                "arg_index": arg_index,
                "prefix": typing_prefix
            }

        return {"type": "general", "prefix": typing_prefix}

    def _infer_object_type(self, obj_expr: str) -> str:
        symbol = self.symbol_table.resolve(obj_expr)
        if symbol:
            return symbol.type
        return None

    def _get_member_completions(self, obj_type: str, prefix: str) -> list:
        if not obj_type:
            return []

        clean_type = obj_type.replace("*", "").strip()
        if clean_type.startswith("struct "):
            struct_name = clean_type[7:].strip()
            completions = []
            struct_scope = getattr(self.symbol_table, 'struct_scopes', {}).get(struct_name)
            
            if struct_scope:
                for name, symbol in struct_scope.symbols.items():
                    if prefix and not name.startswith(prefix):
                        continue
                    completions.append({
                        "label": name,
                        "kind": "field",
                        "type": getattr(symbol, 'type', 'unknown'),
                        "detail": f"{getattr(symbol, 'type', '')} {name}",
                        "sortOrder": self._get_sort_order("field"),
                    })
            return completions
        return []

    def _get_function_arg_completions(self, context: dict, current_line: int, current_col: int) -> list:
        func_name = context.get("func_name")
        arg_index = context.get("arg_index", 0)
        prefix = context.get("prefix", "")

        completions = self._get_scope_completions(prefix, current_line, current_col)
        
        expected_type = None
        if hasattr(self.symbol_table, 'resolve'):
            func_symbol = self.symbol_table.resolve(func_name)
            if func_symbol and func_symbol.kind == "function" and getattr(func_symbol, 'signature', None):
                sig = func_symbol.signature
                if "->" in sig:
                    params_part = sig.split("->")[0].strip().strip("()")
                    if params_part:
                        param_types = [p.strip() for p in params_part.split(",")]
                        if arg_index < len(param_types):
                            expected_type = param_types[arg_index]

        filtered = []
        for comp in completions:
            if comp["kind"] == "type":
                filtered.append(comp)
                continue
                
            if comp["kind"] == "function":
                continue
                
            if expected_type:
                comp_type = comp.get("type", "").replace("[]", "*").strip()
                exp_type = expected_type.replace("[]", "*").strip()
                if comp_type == exp_type or exp_type == "void*":
                    filtered.append(comp)
            else:
                filtered.append(comp)

        return filtered

    def _get_scope_completions(self, prefix: str, current_line: int, current_col: int) -> list:
        completions = []
        
        primitive_types = ["int", "float", "char", "double", "void", "struct"]
        for pt in primitive_types:
            if not prefix or pt.startswith(prefix):
                completions.append({
                    "label": pt,
                    "kind": "type",
                    "type": "keyword",
                    "detail": "primitive type",
                    "sortOrder": self._get_sort_order("type")
                })

        symbols = self._find_active_scope_symbols(current_line, current_col, prefix)
        for symbol in symbols:
            if prefix and not symbol.name.startswith(prefix):
                continue

            kind = getattr(symbol, 'kind', 'variable')
            if kind == "function":
                sig = getattr(symbol, 'signature', None)
                detail = sig if sig else f"{getattr(symbol, 'type', '')} function"
            else:
                detail = f"{getattr(symbol, 'type', '')} {symbol.name}"

            completions.append({
                "label": symbol.name,
                "kind": kind,
                "type": getattr(symbol, 'type', ''),
                "detail": detail,
                "sortOrder": self._get_sort_order(kind),
            })

        completions.sort(key=lambda x: (x["sortOrder"], x["label"]))
        return completions

    def _find_active_scope_symbols(self, current_line: int, current_col: int, prefix: str) -> list:
        symbols = []
        seen = set()

        # ۱. متغیرهای سراسری (با در نظر گرفتن اینکه در همان لحظه در حال تعریف نباشند)
        if hasattr(self.symbol_table, 'global_scope'):
            for name, symbol in self.symbol_table.global_scope.symbols.items():
                def_line, def_col = self._get_loc_details(getattr(symbol, 'definition_loc', None))
                if def_line < current_line or (def_line == current_line and def_col < current_col - len(prefix)):
                    seen.add(name)
                    symbols.append(symbol)

        # ۲. محاسبه مرز توابع
        func_starts = []
        if hasattr(self.symbol_table, 'all_symbols'):
            for symbol in self.symbol_table.all_symbols:
                if symbol.kind == "function":
                    func_starts.append((symbol.name, self._get_loc_details(symbol.definition_loc)[0]))
        
        func_starts.sort(key=lambda x: x[1])
        
        active_func_start = -1
        active_func_end = float('inf')
        
        for i in range(len(func_starts)):
            if func_starts[i][1] <= current_line:
                active_func_start = func_starts[i][1]
                if i + 1 < len(func_starts):
                    active_func_end = func_starts[i+1][1] - 1
                else:
                    active_func_end = float('inf')

        # ۳. استخراج متغیرهای محلی
        if hasattr(self.symbol_table, 'all_symbols'):
            for symbol in self.symbol_table.all_symbols:
                if getattr(symbol, 'scope', '') != "global" and symbol.kind != "struct":
                    def_line, def_col = self._get_loc_details(getattr(symbol, 'definition_loc', None))
                    
                    if active_func_start <= def_line <= current_line:
                        # بررسی اینکه متغیر دقیقاً زیر دست کرسر در حال تعریف نباشد
                        if def_line < current_line or (def_line == current_line and def_col < current_col - len(prefix)):
                            if symbol.name not in seen:
                                seen.add(symbol.name)
                                symbols.append(symbol)

        return symbols

    def _get_loc_details(self, loc) -> tuple:
        """Helper to safely extract (line, column) from definition_loc"""
        if not loc:
            return 0, 0
        try:
            if isinstance(loc, str):
                parts = loc.split(':')
                # پشتیبانی از فرمت‌های "filename:line:col" و "line:col"
                if len(parts) >= 3:
                    return int(parts[-2]), int(parts[-1])
                elif len(parts) == 2:
                    return int(parts[0]), int(parts[1])
                return 0, 0
            
            line = getattr(loc, 'line', 0)
            col = getattr(loc, 'column', getattr(loc, 'col', 0))
            return line, col
        except (IndexError, ValueError, AttributeError):
            return 0, 0

    def _get_sort_order(self, kind: str) -> int:
        priority = {
            "local": 0,
            "parameter": 1,
            "variable": 2,
            "field": 3,
            "type": 4,       
            "function": 5,
            "struct": 6,
            "global": 7,
        }
        return priority.get(kind, 10)