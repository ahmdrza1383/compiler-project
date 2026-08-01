import os
from typing import Dict, Any


class RenameEngine:
    def __init__(self, navigation_engine, source_code: str):
        self.nav = navigation_engine
        self.source_code = source_code

    def rename(self, line: int, col: int, new_name: str) -> Dict[str, Any]:
        symbol = self.nav._find_symbol_at_location(line, col)
        if not symbol:
            return {
                "status": "error",
                "message": "Symbol not found at the specified location.",
            }

        old_name = symbol.name
        if old_name == new_name:
            return {
                "status": "error",
                "message": "The new name is identical to the current name.",
            }


        if symbol.scope and new_name in symbol.scope.symbols:
            return {
                "status": "error",
                "message": f"Conflict Detection: '{new_name}' is already defined in this scope.",
            }

        refs_result = self.nav.find_all_references(line, col)
        if refs_result["status"] != "success":
            return {
                "status": "error",
                "message": "Failed to extract symbol references.",
            }

        references = refs_result["references"]

        references.sort(key=lambda x: (x["line"], x["col"]), reverse=True)

        lines = self.source_code.splitlines(keepends=True)
        old_name_len = len(old_name)

        for ref in references:
            r_line = ref["line"] - 1
            r_col = ref["col"] - 1

            if r_line < len(lines):
                target_line = lines[r_line]

                if target_line[r_col : r_col + old_name_len] == old_name:
                    lines[r_line] = (
                        target_line[:r_col]
                        + new_name
                        + target_line[r_col + old_name_len :]
                    )

        new_source = "".join(lines)

        return {
            "status": "success",
            "old_name": old_name,
            "new_name": new_name,
            "modified_source": new_source,
            "total_replaced": len(references),
        }
