import json
import sys
import os
from anytree import RenderTree

from src.lexer import Lexer
from src.parser import Parser

def read_source_file(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] File '{file_path}' not found.")
        return ""

def write_tokens_to_file(tokens: list, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    token_dicts = [t.to_dict() for t in tokens]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(token_dicts, f, indent=2)
    print(f"[INFO] Tokens successfully written to {output_path}")

def write_ast_json(ast_root, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ast_root.to_dict(), f, indent=2)
    print(f"[INFO] AST (JSON) successfully written to {output_path}")

def write_ast_txt(ast_root, output_path: str):
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

    # ۱. تحلیل لغوی (Lexer)
    lexer = Lexer(source_code, file_name=source_file)
    tokens = []
    while True:
        token = lexer.next_token()
        tokens.append(token)
        if token.type.name == "EOF":
            break

    # ۲. تحلیل نحوی (Parser) و تولید AST در حافظه
    parser = Parser(tokens)
    ast_root = parser.parse()

    # چاپ خطاهای سینتکسی (Panic Mode)
    if parser.errors:
        print("\n[!] SYNTAX ERRORS FOUND:")
        for err in parser.errors:
            print(f"  -> {err}")
        print("-" * 50)

    # ۳. تولید خروجی‌ها به صورت یکجا
    write_tokens_to_file(tokens, "outputs/tokens.json")
    write_ast_json(ast_root, "outputs/ast.json")
    write_ast_txt(ast_root, "outputs/ast.txt")
    
    # چاپ بخشی از درخت برای دیباگ در کنسول
    print("=" * 50)
    print("AST PREVIEW (DEBUG)")
    print("=" * 50)
    for pre, fill, node in RenderTree(ast_root):
        print(f"{pre}{node.name}")
        # برای کوتاه شدن لاگ فقط ۵۰ خط اول چاپ می‌شود
        if node.depth > 15: 
            pass

if __name__ == "__main__":
    main()