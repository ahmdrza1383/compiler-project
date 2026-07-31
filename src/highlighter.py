from src.token import TokenType
from src.ast_node import SymbolCategory


class SyntaxHighlighter:
    def __init__(self, source_code: str, ast_root=None, tokens: list = None):
        self.source_code = source_code
        self.ast_root = ast_root
        self.tokens = tokens if tokens is not None else []
        self.tokens_meta = []

    def _add_token(self, lexeme: str, line: int, col: int, category: str):
        self.tokens_meta.append({
            'lexeme': lexeme,
            'line': line,
            'col': col,
            'category': category
        })

    def extract_tokens(self) -> list:
        self.tokens_meta = []

        # ۱. پردازش لکسر و توکن‌ها
        for token in self.tokens:
            line = token.location.line
            col = token.location.column
            lexeme = token.lexeme
            t_type = token.type

            category = None

            if t_type == TokenType.KEYWORD:
                if lexeme in ('int', 'float', 'double', 'char', 'void'):
                    category = 'type_name'
                else:
                    category = 'keyword'

            elif t_type == TokenType.OPERATOR:
                category = 'operator'

            elif t_type in (TokenType.INT_LIT, TokenType.FLOAT_LIT):
                category = 'number'

            elif t_type in (TokenType.CHAR_LIT, TokenType.STRING_LIT):
                category = 'string'

            elif t_type == TokenType.IDENTIFIER:
                # اگر نام شناسه‌ها دقیقاً Vector باشد به عنوان نوع کلاس شناخته شود
                if lexeme == 'Vector':
                    category = 'class_type'
                else:
                    category = 'variable'

            elif t_type == TokenType.INVALID:
                category = 'error'

            if category:
                self._add_token(lexeme, line, col, category)

        # ۲. پیمایش AST برای شناسایی دقیق توابع و کلاس‌ها
        if self.ast_root:
            self._traverse_ast(self.ast_root)

        # ۳. مرتب‌سازی و حذف تکراری‌ها
        seen = set()
        unique_tokens = []
        for token in self.tokens_meta:
            key = (token['line'], token['col'], token['lexeme'])
            if key not in seen:
                seen.add(key)
                unique_tokens.append(token)

        unique_tokens.sort(key=lambda x: (x['line'], x['col']))
        self.tokens_meta = unique_tokens
        return self.tokens_meta

    def _traverse_ast(self, node):
        """پیمایش امن AST برای استخراج توابع و ساختارها بر اساس ویژگی‌های رایج گره‌ها"""
        if node:
            # بررسی ویژگی‌های احتمالی برای نام و نوع گره در AST شما
            node_str = str(node).lower()

            # اگر گره مربوط به تعریف تابع یا کلاس باشد، نام آن را استخراج می‌کنیم
            if hasattr(node, 'name') and node.name:
                lexeme = str(node.name)
                # بررسی موقعیت خط و ستون در صورت وجود
                line = getattr(node, 'line', 1)
                col = getattr(node, 'col', 1)

                if 'func' in node_str or 'function' in node_str:
                    self._add_token(lexeme, line, col, 'function')
                elif 'struct' in node_str or 'class' in node_str or lexeme == 'Vector':
                    self._add_token(lexeme, line, col, 'class_type')

            # پیمایش فرزندان
            if hasattr(node, 'children') and node.children:
                for child in node.children:
                    self._traverse_ast(child)

    def to_ansi(self) -> str:
        if not self.tokens_meta:
            self.extract_tokens()
        return self.source_code

    def to_html(self) -> str:
        if not self.tokens_meta:
            self.extract_tokens()

        lines = self.source_code.splitlines()
        tokens_by_line = {}
        for t in self.tokens_meta:
            l = t['line']
            if l not in tokens_by_line:
                tokens_by_line[l] = []
            tokens_by_line[l].append(t)

        highlighted_lines = []
        for line_idx, line_text in enumerate(lines, start=1):
            if line_idx not in tokens_by_line:
                highlighted_lines.append(line_text)
                continue

            line_tokens = sorted(tokens_by_line[line_idx], key=lambda x: x['col'], reverse=True)

            new_line = line_text
            for t in line_tokens:
                col = t['col'] - 1
                lexeme = t['lexeme']
                cat = t['category']

                if 0 <= col < len(new_line):
                    wrapped = f'<span class="{cat}">{lexeme}</span>'
                    new_line = new_line[:col] + wrapped + new_line[col + len(lexeme):]

            highlighted_lines.append(new_line)

        formatted_code = "\n".join(highlighted_lines)

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Syntax Highlighted Code</title>
    <style>
        body {{ background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace; padding: 20px; }}
        pre {{ line-height: 1.5; }}
        .keyword {{ color: #569cd6; font-weight: bold; }}
        .type_name {{ color: #4ec9b0; }}
        .class_type {{ color: #4ec9b0; font-weight: bold; }}
        .function {{ color: #dcdcaa; }}
        .variable {{ color: #9cdcfe; }}
        .number {{ color: #b5cea8; }}
        .string {{ color: #6a9955; }}
        .operator {{ color: #d4d4d4; }}
        .error {{ color: #f44747; text-decoration: underline wavy #f44747; }}
    </style>
</head>
<body>
    <pre>{formatted_code}</pre>
</body>
</html>"""
        return html_template