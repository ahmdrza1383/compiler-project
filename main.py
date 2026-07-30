import json
import sys
import os
from src.lexer import Lexer
from src.token import Token


def read_source_file(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] File '{file_path}' not found.")
        return ""


def write_tokens_to_file(tokens: list[Token], output_path: str):
    """توکن‌ها را به صورت JSON در فایل ذخیره می‌کند"""
    token_dicts = [t.to_dict() for t in tokens]
    # ایجاد پوشه output اگر وجود نداشته باشد
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(token_dicts, f, indent=2)
    print(f"[INFO] Tokens successfully written to {output_path}")


def main():
    # ورودی: فایل کد منبع
    source_file = "test_code.c"
    # اگر آرگومان خط فرمان داده شد، آن را بگیر
    if len(sys.argv) > 1:
        source_file = sys.argv[1]

    source_code = read_source_file(source_file)
    if not source_code:
        return

    # ۱. ایجاد لکسر
    lexer = Lexer(source_code, file_name=source_file)

    # ۲. تحلیل و تولید لیست توکن‌ها
    tokens = []
    while True:
        token = lexer.next_token()
        tokens.append(token)
        if token.type.name == "EOF":
            break

    # ۳. چاپ در کنسول برای دیباگ سریع
    print("=" * 50)
    print("LEXER OUTPUT (DEBUG)")
    print("=" * 50)
    for t in tokens:
        print(f"[{t.type.value:12}] {t.lexeme:15} \t@ {t.location}")

    # ۴. ذخیره در فایل JSON برای مراحل بعدی
    write_tokens_to_file(tokens, "outputs/tokens.json")


if __name__ == "__main__":
    main()
