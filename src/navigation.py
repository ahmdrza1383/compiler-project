class NavigationEngine:
    def __init__(self, symbol_table, ast_root=None):
        self.symbol_table = symbol_table
        self.ast_root = ast_root

    def _find_symbol_at_location(self, line: int, col: int):
        for sym in self.symbol_table.all_symbols:
            name_len = len(sym.name) if sym.name else 0
            
            if sym.definition_loc:
                d_line = getattr(sym.definition_loc, 'line', -1)
                d_col = getattr(sym.definition_loc, 'column', getattr(sym.definition_loc, 'col', -1))
                if d_line == line and d_col <= col <= d_col + name_len:
                    return sym
                    
            for ref in sym.references:
                if hasattr(ref, 'line') or hasattr(ref, 'column') or hasattr(ref, 'col'):
                    r_line = getattr(ref, 'line', -1)
                    r_col = getattr(ref, 'column', getattr(ref, 'col', -1))
                    if r_line == line and r_col <= col <= r_col + name_len:
                        return sym
                elif isinstance(ref, str):
                    parts = ref.split(':')
                    if len(parts) >= 3:
                        try:
                            r_line, r_col = int(parts[1]), int(parts[2])
                            if r_line == line and r_col <= col <= r_col + name_len:
                                return sym
                        except ValueError:
                            continue

        # --- فقط این بخش را به انتهای کدهای قبلی خود (قبل از return None) اضافه کنید ---
        if hasattr(self.symbol_table, 'struct_scopes'):
            for struct_name, scope in self.symbol_table.struct_scopes.items():
                for sym in scope.symbols.values():
                    # بررسی تطابق با محل تعریف
                    if sym.definition_loc and sym.definition_loc.line == line and sym.definition_loc.column <= col <= sym.definition_loc.column + len(sym.name):
                        return sym
                    
                    # بررسی تطابق با ارجاعات
                    for ref in sym.references:
                        if hasattr(ref, 'line') and ref.line == line and ref.column <= col <= ref.column + len(sym.name):
                            return sym
        # -------------------------------------------------------------------------------
        
        return None

    def goto_definition(self, line: int, col: int) -> dict:
        symbol = self._find_symbol_at_location(line, col)
        if not symbol or not symbol.definition_loc:
            return {"status": "error", "message": "Symbol or definition not found"}
        
        return {
            "status": "success",
            "symbol": symbol.name,
            "kind": symbol.kind,
            "type": symbol.type,
            "defined_at": {
                "file": symbol.definition_loc.file_name,
                "line": symbol.definition_loc.line,
                "col": symbol.definition_loc.column
            }
        }

    def find_all_references(self, line: int, col: int) -> dict:
        symbol = self._find_symbol_at_location(line, col)
        if not symbol:
            return {"status": "error", "message": "Symbol not found"}
            
        refs = []
        added_locations = set()
        
        if symbol.definition_loc:
            refs.append({
                "file": symbol.definition_loc.file_name,
                "line": symbol.definition_loc.line,
                "col": symbol.definition_loc.column,
                "is_definition": True
            })
            added_locations.add((symbol.definition_loc.line, symbol.definition_loc.column))
            
        for ref in symbol.references:
            if hasattr(ref, 'line') and hasattr(ref, 'column'):
                r_file = getattr(ref, 'file_name', 'test_code.c')
                r_line, r_col = ref.line, ref.column
                if (r_line, r_col) not in added_locations:
                    refs.append({
                        "file": r_file,
                        "line": r_line,
                        "col": r_col,
                        "is_definition": False
                    })
                    added_locations.add((r_line, r_col))
            elif isinstance(ref, str):
                parts = ref.split(':')
                if len(parts) >= 3:
                    r_file = parts[0]
                    try:
                        r_line, r_col = int(parts[1]), int(parts[2])
                        if (r_line, r_col) not in added_locations:
                            refs.append({
                                "file": r_file,
                                "line": r_line,
                                "col": r_col,
                                "is_definition": False
                            })
                            added_locations.add((r_line, r_col))
                    except ValueError:
                        continue
                    
        return {
            "status": "success",
            "symbol": symbol.name,
            "total_references": len(refs),
            "references": refs
        }

    def get_hover_info(self, line: int, col: int) -> dict:
        symbol = self._find_symbol_at_location(line, col)
        if not symbol:
            return {"status": "error", "message": "No symbol info available at this location"}
            
        type_str = str(symbol.type) if symbol.type else "unknown"
        if symbol.kind == "function" and getattr(symbol, "signature", None):
            type_str = symbol.signature
            
        scope_str = "global"
        if hasattr(symbol, "scope") and symbol.scope:
            if hasattr(symbol.scope, "scope_type"):
                scope_str = symbol.scope.scope_type
            elif hasattr(symbol.scope, "name"):
                scope_str = symbol.scope.name
            elif isinstance(symbol.scope, str):
                scope_str = symbol.scope
            else:
                scope_str = "local"
                
        return {
            "status": "success",
            "hover": {
                "symbol": symbol.name,
                "kind": symbol.kind,
                "type": type_str,
                "scope": scope_str,
                "initialized": bool(symbol.is_initialized),
                "used": bool(symbol.is_used)
            }
        }