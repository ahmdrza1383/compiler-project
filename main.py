import json
import sys
import os
from anytree import RenderTree

from src.lexer import Lexer
from src.token import TokenType
from src.parser import Parser
from src.error_reporter import ErrorReporter, Severity
from src.highlighter import SyntaxHighlighter
from src.symbol_table_builder import SymbolTableBuilder
from src.type_checker import TypeChecker
from src.auto_completer import AutoCompleter


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
    print(f"[INFO] Tokens written to {output_path}")


def write_tokens_to_text_file(tokens: list, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"{'TOKEN TYPE':<15} | {'LEXEME':<25} | {'LOCATION'}\n")
        f.write("-" * 65 + "\n")
        for t in tokens:
            safe_lexeme = t.lexeme.replace("\n", "\\n").replace("\r", "\\r")
            f.write(f"[{t.type.value:<13}] | {safe_lexeme:<25} | {t.location}\n")
    print(f"[INFO] Tokens text written to {output_path}")


def write_ast_json(ast_root, output_path: str):
    if not ast_root:
        return
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ast_root.to_dict(), f, indent=2)
    print(f"[INFO] AST JSON written to {output_path}")


def write_ast_txt(ast_root, output_path: str):
    if not ast_root:
        return
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for pre, fill, node in RenderTree(ast_root):
            f.write(f"{pre}{node.name}\n")
    print(f"[INFO] AST text written to {output_path}")


def write_symbol_table_txt(symbol_table, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("SYMBOL TABLE\n")
        f.write("=" * 70 + "\n")
        _print_scope_text(symbol_table.global_scope, 0, f)
        f.write("=" * 70 + "\n")


def _print_scope_text(scope, indent: int, file):
    prefix = "  " * indent
    file.write(f"{prefix}Scope: {scope.scope_type}\n")
    for name, symbol in scope.symbols.items():
        loc = symbol.definition_loc
        refs = len(symbol.references)
        init = "yes" if symbol.is_initialized else "no"
        used = "yes" if symbol.is_used else "no"
        file.write(
            f"{prefix}  [{symbol.kind}] '{name}' : {symbol.type}  "
            f"(def: {loc.line}:{loc.column}, init={init}, used={used}, refs={refs})\n"
        )
    for child in scope.children:
        _print_scope_text(child, indent + 1, file)


def write_semantic_report_txt(errors, warnings, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("SEMANTIC REPORT\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total Errors: {len(errors)}\n")
        f.write(f"Total Warnings: {len(warnings)}\n")
        f.write("-" * 70 + "\n")
        if errors:
            f.write("\nERRORS:\n")
            for i, err in enumerate(errors, 1):
                f.write(f"  {i}. {err}\n")
        if warnings:
            f.write("\nWARNINGS:\n")
            for i, warn in enumerate(warnings, 1):
                f.write(f"  {i}. {warn}\n")
        if not errors and not warnings:
            f.write("\nNo semantic errors or warnings found.\n")
        f.write("=" * 70 + "\n")


def write_type_report_txt(errors, warnings, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("TYPE REPORT\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total Type Errors: {len(errors)}\n")
        f.write(f"Total Type Warnings: {len(warnings)}\n")
        f.write("-" * 70 + "\n")
        if errors:
            f.write("\nERRORS:\n")
            for i, err in enumerate(errors, 1):
                f.write(f"  {i}. {err}\n")
        if warnings:
            f.write("\nWARNINGS:\n")
            for i, warn in enumerate(warnings, 1):
                f.write(f"  {i}. {warn}\n")
        if not errors and not warnings:
            f.write("\nNo type errors or warnings found.\n")
        f.write("=" * 70 + "\n")


def main():
    source_file = "test_code.c"
    if len(sys.argv) > 1:
        source_file = sys.argv[1]

    source_code = read_source_file(source_file)
    if not source_code:
        return

    print(f"[INFO] Compiling {source_file} ...")

    reporter = ErrorReporter()

    lexer = Lexer(source_code, file_name=source_file, reporter=reporter)
    tokens = []
    while True:
        token = lexer.next_token()
        tokens.append(token)
        if token.type == TokenType.EOF:
            break

    parser = Parser(tokens, reporter)
    ast_root = None
    try:
        ast_root = parser.parse()
    except Exception as e:
        print(f"[ERROR] Parsing error: {e}")

    if reporter.has_errors():
        print("[!] Syntax errors found.")
    else:
        print("[OK] No syntax errors.")

    write_tokens_to_file(tokens, "outputs/tokens.json")
    write_tokens_to_text_file(tokens, "outputs/tokens.txt")

    if ast_root:
        write_ast_json(ast_root, "outputs/ast.json")
        write_ast_txt(ast_root, "outputs/ast.txt")

    reporter.export_txt("outputs/errors_log.txt")
    reporter.export_json("outputs/errors_log.json")

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

    html_path = "outputs/highlighted_code.html"
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(highlighter.to_html())
    print(f"[INFO] HTML highlighting saved to {html_path}")

    if ast_root:
        builder = SymbolTableBuilder(ast_root, source_file, verbose=False)
        symbol_table = builder.get_symbol_table()
        semantic_errors = builder.get_errors()
        semantic_warnings = builder.warnings

        st_path = "outputs/symbol_table.json"
        os.makedirs(os.path.dirname(st_path), exist_ok=True)
        with open(st_path, "w", encoding="utf-8") as f:
            json.dump(symbol_table.to_dict(), f, indent=2)
        print(f"[INFO] Symbol table JSON saved to {st_path}")

        st_txt_path = "outputs/symbol_table.txt"
        write_symbol_table_txt(symbol_table, st_txt_path)
        print(f"[INFO] Symbol table text saved to {st_txt_path}")

        type_checker = TypeChecker(symbol_table)
        type_checker.check(ast_root)
        type_errors = type_checker.errors
        type_warnings = type_checker.warnings

        if type_errors:
            print("[!] Type errors found.")
        else:
            print("[OK] No type errors.")

        if type_errors or type_warnings:
            type_output_path = "outputs/type_errors.json"
            with open(type_output_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"errors": type_errors, "warnings": type_warnings}, f, indent=2
                )
            print(f"[INFO] Type errors saved to {type_output_path}")

            type_report_path_txt = "outputs/type_report.txt"
            write_type_report_txt(type_errors, type_warnings, type_report_path_txt)
            print(f"[INFO] Type report text saved to {type_report_path_txt}")

        completer = AutoCompleter(symbol_table, ast_root)
        completions = completer.get_completions(source_code, 3, 10)
        if completions:
            completion_path = "outputs/completions.json"
            with open(completion_path, "w", encoding="utf-8") as f:
                json.dump(completions, f, indent=2)
            print(f"[INFO] Auto-completion results saved to {completion_path}")

        all_errors = semantic_errors + type_errors
        all_warnings = semantic_warnings + type_warnings

        semantic_report_path_json = "outputs/semantic_report.json"
        with open(semantic_report_path_json, "w", encoding="utf-8") as f:
            json.dump({"errors": all_errors, "warnings": all_warnings}, f, indent=2)
        print(f"[INFO] Semantic report JSON saved to {semantic_report_path_json}")

        semantic_report_path_txt = "outputs/semantic_report.txt"
        write_semantic_report_txt(all_errors, all_warnings, semantic_report_path_txt)
        print(f"[INFO] Semantic report text saved to {semantic_report_path_txt}")

        if all_errors:
            print("[!] Semantic errors found:")
            for err in all_errors:
                print(f"  ERROR: {err}")
        if all_warnings:
            print("[!] Semantic warnings found:")
            for warn in all_warnings:
                print(f"  WARNING: {warn}")
        if not all_errors and not all_warnings:
            print("[OK] No semantic errors or warnings.")

    else:
        print("[ERROR] No AST available for semantic analysis.")


if __name__ == "__main__":
    main()
