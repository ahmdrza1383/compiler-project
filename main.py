import json
import sys
import os
from anytree import RenderTree

from src.lexer import Lexer
from src.token import TokenType
from src.parser import Parser
from src.error_reporter import ErrorReporter, Severity
from src.highlighter import SyntaxHighlighter
from src.symbol_table_builder import SymbolTableBuilder  # <-- جدید
from src.symbol_table import SymbolTable


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


def write_tokens_to_text_file(tokens: list, output_path: str):
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


def main():
    source_file = "test_code.c"
    if len(sys.argv) > 1:
        source_file = sys.argv[1]

    source_code = read_source_file(source_file)
    if not source_code:
        return

    print(f"[INFO] Compiling {source_file} ...\n")

    reporter = ErrorReporter()

    # ---- Lexer ----
    lexer = Lexer(source_code, file_name=source_file, reporter=reporter)
    tokens = []
    while True:
        token = lexer.next_token()
        tokens.append(token)
        if token.type == TokenType.EOF:
            break

    # ---- Parser ----
    parser = Parser(tokens, reporter)
    ast_root = None
    try:
        ast_root = parser.parse()
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during parsing: {e}")

    # ---- گزارش خطاهای نحوی ----
    if reporter.has_errors():
        print("\n[!] SYNTAX ERRORS FOUND:")
        for diag in reporter.diagnostics:
            print(f"  -> {diag}")
        print("-" * 50)
    else:
        print("\n[OK] No syntax errors found.")
        print("-" * 50)

    # ---- ذخیره خروجی‌های فاز ۱ ----
    write_tokens_to_file(tokens, "outputs/tokens.json")
    write_tokens_to_text_file(tokens, "outputs/tokens.txt")

    if ast_root:
        write_ast_json(ast_root, "outputs/ast.json")
        write_ast_txt(ast_root, "outputs/ast.txt")

    reporter.export_txt("outputs/errors_log.txt")
    reporter.export_json("outputs/errors_log.json")
    print("[INFO] Error logs written to outputs/errors_log.{txt,json}")

    # ---- هایلایت کردن (فاز ۱) ----
    print("\n" + "=" * 60)
    print("PHASE 1: SYNTAX HIGHLIGHTING (Section 4.4 & 4.5)")
    print("=" * 60)

    parser_errors = []
    if reporter.has_errors():
        for diag in reporter.diagnostics:
            if hasattr(diag, "severity") and diag.severity == Severity.ERROR:
                parser_errors.append(
                    {
                        "line": diag.line,
                        "col": diag.col,
                        "length": diag.length if hasattr(diag, "length") else 1,
                    }
                )

    highlighter = SyntaxHighlighter(source_code, ast_root, tokens, parser_errors)
    highlighter.extract_tokens()

    print("\n📺 ANSI Output (first 20 lines):")
    print("-" * 40)
    ansi_output = highlighter.to_ansi()
    print("\n".join(ansi_output.split("\n")[:20]))  # فقط ۲۰ خط اول
    print("-" * 40)

    html_path = "outputs/highlighted_code.html"
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(highlighter.to_html())
    print(f"\nHTML saved to: {html_path}")

    # ---- فاز ۲: جدول نمادها (بدون پرینت اضافه) ----
    print("\n" + "=" * 70)
    print("PHASE 2: SYMBOL TABLE (بخش 5.1)")
    print("=" * 70)

    if ast_root:
        builder = SymbolTableBuilder(
            ast_root, source_file, verbose=False
        )  # خاموش کردن پرینت
        symbol_table = builder.get_symbol_table()
        semantic_errors = builder.get_errors()

        if semantic_errors:
            print("\n SEMANTIC ERRORS FOUND (بخش 5.5):")
            for err in semantic_errors:
                print(f"  {err}")
        else:
            print("\nNO SEMANTIC ERRORS FOUND")

        # ذخیره جدول به فایل JSON
        st_path = "outputs/symbol_table.json"
        os.makedirs(os.path.dirname(st_path), exist_ok=True)
        with open(st_path, "w", encoding="utf-8") as f:
            json.dump(symbol_table.to_dict(), f, indent=2)
        print(f"\n[INFO] Symbol Table saved to {st_path}")
    else:
        print("No AST available to build Symbol Table")


if __name__ == "__main__":
    main()
