import json
import sys
import os
from src.highlighter import SyntaxHighlighter as ASTHighlighter
from anytree import RenderTree

from src.lexer import Lexer
from src.token import TokenType
from src.parser import Parser
from src.error_reporter import ErrorReporter


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
    # ===== هایلایت کردن با ASTHighlighter =====
    print("\n" + "=" * 60)
    print("🎨 PHASE 1: SYNTAX HIGHLIGHTING (Section 4.4 & 4.5)")
    print("=" * 60)

    # ایجاد هایلایتر
    highlighter = ASTHighlighter(source_code, ast_root, tokens)
    highlighter.extract_tokens()

    # خروجی ANSI
    print("\n📺 ANSI Output:")
    print("-" * 40)
    print(highlighter.to_ansi())
    print("-" * 40)

    # خروجی HTML
    html_path = "outputs/highlighted_code.html"
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(highlighter.to_html())
    print(f"\n✅ HTML saved to: {html_path}")
    print("   (Open this file in your browser to see colored code)")


if __name__ == "__main__":
    main()
