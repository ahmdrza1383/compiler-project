import json
import sys
import os
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

    # ۳. تولید خروجی‌ها به صورت یکجا
    write_tokens_to_file(tokens, "outputs/tokens.json")
    if ast_root:
        write_ast_json(ast_root, "outputs/ast.json")
        write_ast_txt(ast_root, "outputs/ast.txt")

    # خروجی گرفتن از فایل‌های لاگ خطا
    reporter.export_txt("outputs/errors_log.txt")
    reporter.export_json("outputs/errors_log.json")
    print(
        "[INFO] Error logs successfully written to outputs/errors_log.txt and outputs/errors_log.json"
    )


if __name__ == "__main__":
    main()
