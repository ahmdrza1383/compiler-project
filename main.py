import json
import sys
import os
from src.highlighter import SyntaxHighlighter
from anytree import RenderTree

from src.lexer import Lexer
from src.token import TokenType
from src.parser import Parser
from src.error_reporter import ErrorReporter, Severity
from src.symbol_table import Symbol, SymbolTable
from src.token import SourceLocation
from src.ast_node import (
    FunctionDef, FunctionDecl, StructDef, VarDecl,
    Identifier, Block, IfStmt, WhileStmt, ForStmt, ReturnStmt,
    BinaryExpr, UnaryExpr, CallExpr, MemberAccess
)


def read_source_file(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] File '{file_path}' not found.")
        return ""


def write_tokens_to_file(tokens: list, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    token_dicts = [t.to_dict() if hasattr(t, "to_dict") else t.__dict__ for t in tokens]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(token_dicts, f, indent=2)
    print(f"[INFO] Tokens successfully written to {output_path}")


def write_tokens_to_text_file(tokens: list["Token"], output_path: str):
    """توکن‌ها را به صورت متنی و جدولی در فایل ذخیره می‌کند"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"{'TOKEN TYPE':<15} | {'LEXEME':<25} | {'LOCATION'}\n")
        f.write("-" * 65 + "\n")

        for t in tokens:
            safe_lexeme = t.lexeme.replace("\n", "\\n").replace("\r", "\\r")

            f.write(f"[{t.type.value:<13}] | {safe_lexeme:<25} | {t.location}\n")

    print(f"[INFO] Tokens text successfully written to {output_path}")


def write_ast_json(ast_root, output_path: str):
    if not ast_root:
        return
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ast_root.to_dict(), f, indent=2)
    print(f"[INFO] AST (JSON) successfully written to {output_path}")


def write_ast_txt(ast_root, output_path: str):
    if not ast_root:
        return
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for pre, fill, node in RenderTree(ast_root):
            f.write(f"{pre}{node.name}\n")
    print(f"[INFO] AST (TXT Tree) successfully written to {output_path}")


def tokenize_source(
        code: str, filename: str = "<stdin>", reporter: ErrorReporter = None
):
    if reporter is None:
        reporter = ErrorReporter()

    lexer = Lexer(code, filename, reporter)
    tokens = []

    while True:
        token = lexer.next_token()
        tokens.append(token)
        if token.type == TokenType.EOF:
            break

    return tokens, reporter.diagnostics


# ============================================
# کلاس SymbolTableBuilder (فاز 2 - بخش 5.1)
# ============================================

class SymbolTableBuilder:
    def __init__(self, ast_root, source_file="<stdin>"):
        self.ast_root = ast_root
        self.source_file = source_file
        self.symbol_table = SymbolTable()
        self.errors = []

        if not ast_root:
            return

        print("\n📌 PASS 1: Declaration Scan (بخش 5.1.2)")
        print("-" * 50)
        self._pass1_declaration_scan(self.ast_root)

        print("\n📌 PASS 2: Resolution Pass (بخش 5.1.2)")
        print("-" * 50)
        self._pass2_resolution(self.ast_root)

    def _make_location(self, node) -> SourceLocation:
        if hasattr(node, 'line') and hasattr(node, 'col'):
            return SourceLocation(self.source_file, node.line, node.col)
        return SourceLocation(self.source_file, 0, 0)

    def _pass1_declaration_scan(self, node):
        if not node:
            return

        if isinstance(node, (FunctionDef, FunctionDecl)):
            func_name = node.func_name.id_name
            params = []
            for param in node.params:
                if hasattr(param, 'var_type'):
                    params.append(param.var_type.type_name)
            return_type = node.return_type.type_name if hasattr(node, 'return_type') else 'void'
            signature = f"({', '.join(params)}) -> {return_type}"

            loc = self._make_location(node.func_name)
            func_symbol = Symbol(
                name=func_name,
                kind="function",
                type_spec=return_type,
                definition_loc=loc,
                signature=signature
            )
            self.symbol_table.define(func_symbol)
            print(f"  ✅ Registered function: {func_name} {signature}")

        elif isinstance(node, StructDef):
            struct_name = node.struct_name.id_name
            loc = self._make_location(node.struct_name)
            struct_symbol = Symbol(
                name=struct_name,
                kind="struct",
                type_spec=f"struct {struct_name}",
                definition_loc=loc
            )
            self.symbol_table.define(struct_symbol)
            print(f"  ✅ Registered struct: {struct_name}")

            if hasattr(node, 'fields'):
                for field in node.fields:
                    if isinstance(field, VarDecl):
                        field_name = field.var_name.id_name
                        field_type = field.var_type.type_name if hasattr(field, 'var_type') else 'unknown'
                        loc = self._make_location(field.var_name)
                        field_symbol = Symbol(
                            name=field_name,
                            kind="field",
                            type_spec=field_type,
                            definition_loc=loc
                        )
                        self.symbol_table.define(field_symbol)
                        print(f"    ✅ Registered field: {field_name} : {field_type}")

        elif isinstance(node, VarDecl):
            # فقط متغیرهای گلوبال واقعی (نه فیلدهای ساختار)
            if self.symbol_table.current_scope == self.symbol_table.global_scope:
                parent = node.parent
                if not isinstance(parent, StructDef):
                    var_name = node.var_name.id_name
                    var_type = node.var_type.type_name if hasattr(node, 'var_type') else 'unknown'
                    loc = self._make_location(node.var_name)
                    var_symbol = Symbol(
                        name=var_name,
                        kind="variable",
                        type_spec=var_type,
                        definition_loc=loc
                    )
                    self.symbol_table.define(var_symbol)
                    print(f"  ✅ Registered global variable: {var_name} : {var_type}")

        for child in node.children:
            self._pass1_declaration_scan(child)

    def _pass2_resolution(self, node):
        if not node:
            return

        if isinstance(node, FunctionDef):
            func_name = node.func_name.id_name
            print(f"\n  🔍 Analyzing function: {func_name}")

            self.symbol_table.enter_scope("function")

            for param in node.params:
                if hasattr(param, 'var_name'):
                    param_name = param.var_name.id_name
                    param_type = param.var_type.type_name if hasattr(param, 'var_type') else 'unknown'
                    loc = self._make_location(param.var_name)
                    param_symbol = Symbol(
                        name=param_name,
                        kind="parameter",
                        type_spec=param_type,
                        definition_loc=loc,
                        is_initialized=True
                    )
                    self.symbol_table.define(param_symbol)
                    print(f"    ✅ Registered parameter: {param_name} : {param_type}")

            if hasattr(node, 'body'):
                self._pass2_resolution(node.body)

            self.symbol_table.exit_scope()
            print(f"  ✅ Finished analyzing: {func_name}")
            return

        elif isinstance(node, Block):
            self.symbol_table.enter_scope("block")
            for stmt in node.statements if hasattr(node, 'statements') else []:
                self._pass2_resolution(stmt)
            self.symbol_table.exit_scope()
            return

        elif isinstance(node, VarDecl):
            var_name = node.var_name.id_name
            var_type = node.var_type.type_name if hasattr(node, 'var_type') else 'unknown'

            existing = self.symbol_table.resolve(var_name)
            if existing:
                line = node.var_name.line if hasattr(node.var_name, 'line') else 0
                col = node.var_name.col if hasattr(node.var_name, 'col') else 0
                self.errors.append(f"Duplicate declaration: {var_name} at {line}:{col}")
                print(f"    ⚠️  Duplicate: {var_name}")
                return

            loc = self._make_location(node.var_name)
            var_symbol = Symbol(
                name=var_name,
                kind="variable",
                type_spec=var_type,
                definition_loc=loc
            )
            self.symbol_table.define(var_symbol)
            print(f"    ✅ Registered variable: {var_name} : {var_type}")

            if hasattr(node, 'initializer') and node.initializer:
                var_symbol.set_initialized()
                self._pass2_resolution(node.initializer)
            return

        elif isinstance(node, Identifier):
            symbol = self.symbol_table.resolve(node.id_name)
            if symbol:
                symbol.set_used()
                loc = self._make_location(node)
                symbol.add_reference(loc)
                print(f"    🔍 Resolved reference: {node.id_name} -> {symbol.kind}")
            else:
                line = node.line if hasattr(node, 'line') else 0
                col = node.col if hasattr(node, 'col') else 0
                self.errors.append(f"Undefined symbol: {node.id_name} at {line}:{col}")
                print(f"    ❌ Undefined: {node.id_name}")
            return

        elif isinstance(node, CallExpr):
            if hasattr(node, 'func_name') and isinstance(node.func_name, Identifier):
                func_name = node.func_name.id_name
                symbol = self.symbol_table.resolve(func_name)
                if symbol:
                    symbol.set_used()
                    loc = self._make_location(node.func_name)
                    symbol.add_reference(loc)
                    print(f"    📞 Call to function: {func_name}")
                else:
                    line = node.func_name.line if hasattr(node.func_name, 'line') else 0
                    col = node.func_name.col if hasattr(node.func_name, 'col') else 0
                    self.errors.append(f"Undefined function: {func_name} at {line}:{col}")
                    print(f"    ❌ Undefined function: {func_name}")

            for arg in node.args if hasattr(node, 'args') else []:
                self._pass2_resolution(arg)
            return

        elif isinstance(node, (BinaryExpr, UnaryExpr)):
            if hasattr(node, 'left'):
                self._pass2_resolution(node.left)
            if hasattr(node, 'right'):
                self._pass2_resolution(node.right)
            if hasattr(node, 'operand'):
                self._pass2_resolution(node.operand)
            return

        elif isinstance(node, MemberAccess):
            if hasattr(node, 'obj'):
                self._pass2_resolution(node.obj)
            if hasattr(node, 'member'):
                self._pass2_resolution(node.member)
            return

        elif isinstance(node, IfStmt):
            if hasattr(node, 'condition'):
                self._pass2_resolution(node.condition)
            if hasattr(node, 'then_branch'):
                self._pass2_resolution(node.then_branch)
            if hasattr(node, 'else_branch'):
                self._pass2_resolution(node.else_branch)
            return

        elif isinstance(node, WhileStmt):
            if hasattr(node, 'condition'):
                self._pass2_resolution(node.condition)
            if hasattr(node, 'body'):
                self._pass2_resolution(node.body)
            return

        elif isinstance(node, ForStmt):
            if hasattr(node, 'init'):
                self._pass2_resolution(node.init)
            if hasattr(node, 'condition'):
                self._pass2_resolution(node.condition)
            if hasattr(node, 'step'):
                self._pass2_resolution(node.step)
            if hasattr(node, 'body'):
                self._pass2_resolution(node.body)
            return

        elif isinstance(node, ReturnStmt):
            if hasattr(node, 'value') and node.value:
                self._pass2_resolution(node.value)
            return

        for child in node.children:
            self._pass2_resolution(child)

    def get_symbol_table(self):
        return self.symbol_table

    def get_errors(self):
        return self.errors


# ============================================
# تابع اصلی main
# ============================================

def main():
    source_file = "test_code.c"
    if len(sys.argv) > 1:
        source_file = sys.argv[1]

    source_code = read_source_file(source_file)
    if not source_code:
        return

    print(f"[INFO] Compiling {source_file} ...\n")

    reporter = ErrorReporter()

    lexer = Lexer(source_code, file_name=source_file, reporter=reporter)
    tokens = []
    while True:
        token = lexer.next_token()
        tokens.append(token)
        if token.type == TokenType.EOF:
            break

    # ۲. تحلیل نحوی (Parser) و تولید AST در حافظه
    parser = Parser(tokens, reporter)
    ast_root = None

    try:
        ast_root = parser.parse()
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during parsing: {e}")

    if reporter.has_errors():
        print("\n[!] SYNTAX ERRORS FOUND:")
        for diag in reporter.diagnostics:
            print(f"  -> {diag}")
        print("-" * 50)
    else:
        print("\n[OK] No syntax errors found.")
        print("-" * 50)

    write_tokens_to_file(tokens, "outputs/tokens.json")
    write_tokens_to_text_file(tokens, "outputs/tokens.txt")

    if ast_root:
        write_ast_json(ast_root, "outputs/ast.json")
        write_ast_txt(ast_root, "outputs/ast.txt")

    reporter.export_txt("outputs/errors_log.txt")
    reporter.export_json("outputs/errors_log.json")
    print(
        "[INFO] Error logs successfully written to outputs/errors_log.txt and outputs/errors_log.json"
    )

    # ============================================
    # ===== جمع‌آوری خطاهای Parser برای هایلایتر =====
    # ============================================

    parser_errors = []
    if reporter.has_errors():
        for diag in reporter.diagnostics:
            if hasattr(diag, 'severity') and diag.severity == Severity.ERROR:
                parser_errors.append({
                    'line': diag.line,
                    'col': diag.col,
                    'length': diag.length if hasattr(diag, 'length') else 1
                })
            elif not hasattr(diag, 'severity'):
                parser_errors.append({
                    'line': diag.line,
                    'col': diag.col,
                    'length': diag.length if hasattr(diag, 'length') else 1
                })

    # ============================================
    # ===== فاز 1: هایلایت کردن =====
    # ============================================

    print("\n" + "=" * 60)
    print("🎨 PHASE 1: SYNTAX HIGHLIGHTING (Section 4.4 & 4.5)")
    print("=" * 60)

    highlighter = SyntaxHighlighter(source_code, ast_root, tokens, parser_errors)
    highlighter.extract_tokens()

    print("\n📺 ANSI Output:")
    print("-" * 40)
    print(highlighter.to_ansi())
    print("-" * 40)

    html_path = "outputs/highlighted_code.html"
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(highlighter.to_html())
    print(f"\n✅ HTML saved to: {html_path}")
    print("   (Open this file in your browser to see colored code)")

    # ============================================
    # ===== فاز 2: Symbol Table (بخش 5.1) =====
    # ============================================

    print("\n" + "=" * 70)
    print("📋 PHASE 2: SYMBOL TABLE (بخش 5.1)")
    print("=" * 70)

    if ast_root:
        builder = SymbolTableBuilder(ast_root, source_file)
        symbol_table = builder.get_symbol_table()
        semantic_errors = builder.get_errors()

        symbol_table.print_table()

        if semantic_errors:
            print("\n⚠️  SEMANTIC ERRORS FOUND (بخش 5.5):")
            for err in semantic_errors:
                print(f"  ❌ {err}")
        else:
            print("\n✅ NO SEMANTIC ERRORS FOUND")

        st_path = "outputs/symbol_table.json"
        os.makedirs(os.path.dirname(st_path), exist_ok=True)
        with open(st_path, "w", encoding="utf-8") as f:
            json.dump(symbol_table.to_dict(), f, indent=2)
        print(f"\n[INFO] Symbol Table saved to {st_path}")
    else:
        print("❌ No AST available to build Symbol Table")


if __name__ == "__main__":
    main()