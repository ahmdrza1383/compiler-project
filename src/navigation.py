from typing import Optional, Dict, Any, List
from .ast_node import ASTNode, Identifier
from .symbol_table import SymbolTable, Symbol

class NavigationEngine:
    def __init__(self, symbol_table: SymbolTable, ast_root: ASTNode):
        self.symbol_table = symbol_table
        self.ast_root = ast_root

    def _find_node_at(self, node: ASTNode, line: int, col: int) -> Optional[Identifier]:
        """پیمایش بازگشتی درخت AST برای یافتن شناسه در سطر و ستون مشخص شده"""
        if not node:
            return None

        # بررسی اینکه آیا گره فعلی یک شناسه است و در مختصات کرسر قرار دارد
        if isinstance(node, Identifier):
            n_line = getattr(node, 'line', -1)
            n_col = getattr(node, 'col', -1)
            length = len(node.id_name)
            
            # کرسر روی کلمه قرار داشته باشد
            if n_line == line and n_col <= col < (n_col + length):
                return node

        # جستجو در فرزندان
        for child in getattr(node, 'children', []):
            found = self._find_node_at(child, line, col)
            if found:
                return found

        return None

    def _get_symbol_at(self, line: int, col: int) -> Optional[Symbol]:
        """یافتن نماد متصل به گره در محل کرسر"""
        # ۱. جستجو در استفاده‌های بدنه کد (درخت AST)
        node = self._find_node_at(self.ast_root, line, col)
        if node and hasattr(node, 'symbol') and node.symbol:
            return node.symbol

        # ۲. جستجو در محل تعریف نمادها (در صورت کلیک روی خود خط تعریف)
        for sym in self.symbol_table.all_symbols:
            d_loc = sym.definition_loc
            if d_loc:
                d_line = getattr(d_loc, 'line', -1)
                d_col = getattr(d_loc, 'column', getattr(d_loc, 'col', -1))
                if d_line == line and d_col <= col < (d_col + len(sym.name)):
                    return sym

        return None

    def goto_definition(self, line: int, col: int) -> Dict[str, Any]:
        """انتقال به محل تعریف نماد زیر کرسر"""
        symbol = self._get_symbol_at(line, col)
        
        if not symbol or not symbol.definition_loc:
            return {"status": "error", "message": "Symbol or definition not found at this location."}

        d_loc = symbol.definition_loc
        return {
            "status": "success",
            "symbol": symbol.name,
            "kind": symbol.kind,
            "type": symbol.signature if symbol.kind == "function" else symbol.type,
            "defined_at": {
                "file": getattr(d_loc, 'file_name', ''),
                "line": getattr(d_loc, 'line', 0),
                "col": getattr(d_loc, 'column', getattr(d_loc, 'col', 0))
            }
        }

    def find_all_references(self, line: int, col: int) -> Dict[str, Any]:
        """پیدا کردن تمامی ارجاعات به یک نماد"""
        symbol = self._get_symbol_at(line, col)
        
        if not symbol:
            return {"status": "error", "message": "No valid symbol found at this location."}

        refs_list = []
        
        # ۱. اضافه کردن محل تعریف به عنوان اولین ارجاع
        d_loc = symbol.definition_loc
        if d_loc:
            refs_list.append({
                "file": getattr(d_loc, 'file_name', ''),
                "line": getattr(d_loc, 'line', 0),
                "col": getattr(d_loc, 'column', getattr(d_loc, 'col', 0)),
                "is_definition": True
            })

        # ۲. اضافه کردن بقیه ارجاعات از بدنه کد
        for ref in symbol.references:
            refs_list.append({
                "file": getattr(ref, 'file_name', ''),
                "line": getattr(ref, 'line', 0),
                "col": getattr(ref, 'column', getattr(ref, 'col', 0)),
                "is_definition": False
            })

        return {
            "status": "success",
            "symbol": symbol.name,
            "total_references": len(refs_list),
            "references": refs_list
        }

    def get_hover_info(self, line: int, col: int) -> Dict[str, Any]:
        """نمایش اطلاعات شناور برای نماد زیر کرسر"""
        symbol = self._get_symbol_at(line, col)
        
        if not symbol:
            return {"status": "error", "message": "No hover information available."}

        info = {
            "symbol": symbol.name,
            "kind": symbol.kind,
            "type": symbol.signature if symbol.kind == "function" else symbol.type,
            "scope": getattr(symbol.scope, 'scope_type', 'unknown') if symbol.scope else "unknown",
            "initialized": symbol.is_initialized,
            "used": symbol.is_used
        }
        
        return {
            "status": "success",
            "hover": info
        }