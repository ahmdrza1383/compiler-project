from src.token import TokenType
from src.ast_node import (
    ASTNode,
    Identifier,
    Literal,
    SymbolCategory,
    TypeSpecifier,
    FunctionDef,
    FunctionDecl,
    StructDef,
    VarDecl,
    MemberAccess,
    CallExpr,
)


class SyntaxHighlighter:
    CATEGORY_COLORS = {
        "keyword": {"ansi": "\033[34;1m", "css": "#0000FF", "class": "kw"},
        "type_name": {"ansi": "\033[92m", "css": "#00FF00", "class": "type"},
        "class_type": {"ansi": "\033[92;1m", "css": "#00FF00", "class": "class"},
        "function": {"ansi": "\033[33;1m", "css": "#FFD700", "class": "func"},
        "variable": {"ansi": "\033[0m", "css": "#FFFFFF", "class": "ident"},
        "number": {"ansi": "\033[38;5;208m", "css": "#FFA500", "class": "num"},
        "string": {"ansi": "\033[32m", "css": "#32CD32", "class": "str"},
        "char": {"ansi": "\033[32m", "css": "#32CD32", "class": "char"},
        "operator": {"ansi": "\033[37m", "css": "#D3D3D3", "class": "op"},
        "comment": {"ansi": "\033[90m", "css": "#808080", "class": "comment"},
        "preprocessor": {"ansi": "\033[35m", "css": "#FF00FF", "class": "preproc"},
        "error": {"ansi": "\033[41;97m", "css": "#FF0000", "class": "error"},
    }

    def __init__(
        self,
        source_code: str,
        ast_root: ASTNode = None,
        tokens: list = None,
        parser_errors: list = None,
    ):
        self.source_code = source_code
        self.ast_root = ast_root
        self.tokens = tokens if tokens is not None else []
        self.parser_errors = parser_errors if parser_errors is not None else []
        self.tokens_meta = []

        self.function_names = set()
        self.struct_names = set()
        self.type_names = {"int", "float", "double", "char", "void"}

        if self.ast_root:
            self._collect_ast_info(self.ast_root)

    def _collect_ast_info(self, node: ASTNode):
        if not node:
            return

        if isinstance(node, (FunctionDef, FunctionDecl)):
            if hasattr(node, "func_name") and node.func_name:
                if hasattr(node.func_name, "id_name"):
                    self.function_names.add(node.func_name.id_name)

        if isinstance(node, StructDef):
            if hasattr(node, "struct_name") and node.struct_name:
                if hasattr(node.struct_name, "id_name"):
                    self.struct_names.add(node.struct_name.id_name)

        for child in node.children:
            self._collect_ast_info(child)

    def extract_tokens(self) -> list:
        self.tokens_meta = []

        for token in self.tokens:
            category = self._get_token_category(token)
            if category:
                self._add_token(
                    token.lexeme, token.location.line, token.location.column, category
                )

        # 2. اضافه کردن خطاهای Parser (به عنوان error)
        for error in self.parser_errors:
            line = error.get("line", 0)
            col = error.get("col", 0)
            length = error.get("length", 1)

            lexeme = self._get_lexeme_at_position(line, col, length)
            if lexeme:
                self._add_token(lexeme, line, col, "error")

        # 3. تکمیل اطلاعات با AST
        if self.ast_root:
            self._enhance_with_ast(self.ast_root)

        # 4. حذف تکراری‌ها (اولویت با error و اطلاعات AST)
        seen = {}
        for token in self.tokens_meta:
            key = (token["line"], token["col"])
            if key not in seen or self._is_more_important(
                token["category"], seen[key]["category"]
            ):
                seen[key] = token

        self.tokens_meta = list(seen.values())
        self.tokens_meta.sort(key=lambda x: (x["line"], x["col"]))
        return self.tokens_meta

    def _get_lexeme_at_position(self, line: int, col: int, length: int) -> str:
        """دریافت متن در موقعیت مشخص از کد منبع"""
        lines = self.source_code.split("\n")
        if line - 1 < len(lines):
            line_text = lines[line - 1]
            if col - 1 < len(line_text):
                return line_text[col - 1 : col - 1 + length]
        return None

    def _get_token_category(self, token) -> str:
        """تشخیص دسته‌ی رنگی از روی توکن"""
        t_type = token.type
        lexeme = token.lexeme

        if t_type == TokenType.INVALID:
            return "error"

        if t_type == TokenType.DIRECTIVE:
            return "preprocessor"

        if t_type == TokenType.KEYWORD:
            if lexeme in self.type_names:
                return "type_name"
            return "keyword"

        if t_type == TokenType.OPERATOR:
            return "operator"

        if t_type in (TokenType.INT_LIT, TokenType.FLOAT_LIT):
            return "number"

        if t_type == TokenType.STRING_LIT:
            return "string"

        if t_type == TokenType.CHAR_LIT:
            return "char"

        if t_type == TokenType.IDENTIFIER:
            if lexeme in self.function_names:
                return "function"
            if lexeme in self.struct_names:
                return "class_type"
            if self._is_type_identifier(lexeme):
                return "type_name"
            return "variable"

        return None

    def _enhance_with_ast(self, node: ASTNode):
        if not node:
            return

        # توابع
        if isinstance(node, (FunctionDef, FunctionDecl)):
            if hasattr(node, "func_name") and node.func_name:
                if hasattr(node.func_name, "id_name"):
                    name = node.func_name.id_name
                    if hasattr(node.func_name, "line") and hasattr(
                        node.func_name, "col"
                    ):
                        self._add_token(
                            name, node.func_name.line, node.func_name.col, "function"
                        )

        if isinstance(node, StructDef):
            if hasattr(node, "struct_name") and node.struct_name:
                if hasattr(node.struct_name, "id_name"):
                    name = node.struct_name.id_name
                    if hasattr(node.struct_name, "line") and hasattr(
                        node.struct_name, "col"
                    ):
                        self._add_token(
                            name,
                            node.struct_name.line,
                            node.struct_name.col,
                            "class_type",
                        )

            if hasattr(node, "fields") and node.fields:
                for field in node.fields:
                    if isinstance(field, VarDecl):
                        if hasattr(field, "var_name") and field.var_name:
                            if hasattr(field.var_name, "id_name"):
                                name = field.var_name.id_name
                                if hasattr(field.var_name, "line") and hasattr(
                                    field.var_name, "col"
                                ):
                                    self._add_token(
                                        name,
                                        field.var_name.line,
                                        field.var_name.col,
                                        "variable",
                                    )

        if isinstance(node, VarDecl):
            if hasattr(node, "var_name") and node.var_name:
                if hasattr(node.var_name, "id_name"):
                    name = node.var_name.id_name
                    if hasattr(node.var_name, "line") and hasattr(node.var_name, "col"):
                        self._add_token(
                            name, node.var_name.line, node.var_name.col, "variable"
                        )

        if isinstance(node, MemberAccess):
            if hasattr(node, "obj") and node.obj:
                if isinstance(node.obj, Identifier):
                    if hasattr(node.obj, "id_name"):
                        if hasattr(node.obj, "line") and hasattr(node.obj, "col"):
                            self._add_token(
                                node.obj.id_name,
                                node.obj.line,
                                node.obj.col,
                                "variable",
                            )

            if hasattr(node, "member") and node.member:
                if isinstance(node.member, Identifier):
                    if hasattr(node.member, "id_name"):
                        if hasattr(node.member, "line") and hasattr(node.member, "col"):
                            self._add_token(
                                node.member.id_name,
                                node.member.line,
                                node.member.col,
                                "variable",
                            )

        if isinstance(node, CallExpr):
            if hasattr(node, "func_name") and node.func_name:
                if isinstance(node.func_name, Identifier):
                    if hasattr(node.func_name, "id_name"):
                        name = node.func_name.id_name
                        if hasattr(node.func_name, "line") and hasattr(
                            node.func_name, "col"
                        ):
                            self._add_token(
                                name,
                                node.func_name.line,
                                node.func_name.col,
                                "function",
                            )

        for child in node.children:
            self._enhance_with_ast(child)

    def _is_type_identifier(self, lexeme: str) -> bool:
        return lexeme in self.type_names or lexeme in self.struct_names

    def _is_more_important(self, cat1: str, cat2: str) -> bool:
        priority = {
            "error": 100,
            "function": 10,
            "class_type": 9,
            "type_name": 8,
            "keyword": 7,
            "number": 5,
            "string": 4,
            "char": 4,
            "operator": 3,
            "variable": 2,
            "preprocessor": 1,
        }
        return priority.get(cat1, 0) > priority.get(cat2, 0)

    def _add_token(self, lexeme: str, line: int, col: int, category: str):
        self.tokens_meta.append(
            {"lexeme": lexeme, "line": line, "col": col, "category": category}
        )

    def to_ansi(self) -> str:
        if not self.tokens_meta:
            self.extract_tokens()

        if not self.tokens_meta:
            return self.source_code

        lines = self.source_code.split("\n")
        tokens_by_line = {}

        for t in self.tokens_meta:
            line = t["line"]
            if line not in tokens_by_line:
                tokens_by_line[line] = []
            tokens_by_line[line].append(t)

        result = []
        for line_idx, line_text in enumerate(lines, start=1):
            if line_idx not in tokens_by_line:
                result.append(line_text)
                continue

            line_tokens = sorted(
                tokens_by_line[line_idx], key=lambda x: x["col"], reverse=True
            )
            new_line = line_text

            for t in line_tokens:
                col = t["col"] - 1
                lexeme = t["lexeme"]
                cat = t["category"]

                color_info = self.CATEGORY_COLORS.get(cat, {})
                ansi_code = color_info.get("ansi", "\033[0m")
                reset = "\033[0m"

                if 0 <= col < len(new_line):
                    if new_line[col : col + len(lexeme)] == lexeme:
                        new_line = (
                            new_line[:col]
                            + f"{ansi_code}{lexeme}{reset}"
                            + new_line[col + len(lexeme) :]
                        )

            result.append(new_line)

        return "\n".join(result)

    def to_html(self) -> str:
        if not self.tokens_meta:
            self.extract_tokens()

        lines = self.source_code.split("\n")
        tokens_by_line = {}

        for t in self.tokens_meta:
            line = t["line"]
            if line not in tokens_by_line:
                tokens_by_line[line] = []
            tokens_by_line[line].append(t)

        highlighted_lines = []
        for line_idx, line_text in enumerate(lines, start=1):
            if line_idx not in tokens_by_line:
                highlighted_lines.append(self._escape_html(line_text))
                continue

            line_tokens = sorted(
                tokens_by_line[line_idx], key=lambda x: x["col"], reverse=True
            )
            new_line = line_text

            for t in line_tokens:
                col = t["col"] - 1
                lexeme = t["lexeme"]
                cat = t["category"]

                css_class = self.CATEGORY_COLORS.get(cat, {}).get("class", "ident")

                if 0 <= col < len(new_line):
                    if new_line[col : col + len(lexeme)] == lexeme:
                        wrapped = f'<span class="{css_class}">{self._escape_html(lexeme)}</span>'
                        new_line = (
                            new_line[:col] + wrapped + new_line[col + len(lexeme) :]
                        )

            highlighted_lines.append(new_line)

        body = "\n".join(highlighted_lines)
        css = self._generate_css()

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Syntax Highlighted Code</title>
    <style>
        body {{
            background-color: #1e1e1e;
            color: #d4d4d4;
            font-family: 'Consolas', 'Courier New', monospace;
            padding: 20px;
            margin: 0;
        }}
        pre {{
            background-color: #1e1e1e;
            padding: 20px;
            border-radius: 8px;
            overflow: auto;
            font-size: 14px;
            line-height: 1.6;
            tab-size: 4;
            white-space: pre-wrap;
        }}
        {css}
    </style>
</head>
<body>
    <pre>{body}</pre>
</body>
</html>"""

    def _generate_css(self) -> str:
        return """
            .kw { color: #0000FF; font-weight: bold; }
            .type { color: #00FF00; }
            .class { color: #00FF00; font-weight: bold; }
            .func { color: #FFD700; }
            .ident { color: #FFFFFF; }
            .num { color: #FFA500; }
            .str { color: #32CD32; }
            .char { color: #32CD32; }
            .op { color: #D3D3D3; }
            .comment { color: #808080; font-style: italic; }
            .preproc { color: #FF00FF; }
            .error { color: #FF0000; text-decoration: underline; }
        """

    def _escape_html(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
