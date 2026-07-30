import re
from .token import Token, TokenType, SourceLocation


class Lexer:
    def __init__(self, source_code: str, file_name: str = "<stdin>"):
        self.source = source_code
        self.file_name = file_name
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(source_code)

        self.keywords = {
            "if",
            "else",
            "while",
            "for",
            "return",
            "int",
            "float",
            "double",
            "char",
            "void",
            "struct",
            "break",
            "continue",
        }

    def _current_char(self) -> str:
        if self.pos >= self.length:
            return "\0"
        return self.source[self.pos]

    def _advance(self) -> str:
        char = self._current_char()
        if char == "\n":
            self.line += 1
            self.col = 1
        elif char != "\0":
            self.col += 1
        self.pos += 1
        return char

    def _peek(self, offset=1) -> str:
        if self.pos + offset >= self.length:
            return "\0"
        return self.source[self.pos + offset]

    def _skip_whitespace(self):
        while self.pos < self.length and self._current_char() in " \t\r\n":
            self._advance()

    def _read_identifier(self) -> Token:
        start_col = self.col
        lexeme = ""
        while self.pos < self.length and (
            self._current_char().isalnum() or self._current_char() == "_"
        ):
            lexeme += self._advance()

        # بررسی کلیدواژه بودن
        token_type = (
            TokenType.KEYWORD if lexeme in self.keywords else TokenType.IDENTIFIER
        )
        return Token(
            type=token_type,
            lexeme=lexeme,
            location=SourceLocation(self.file_name, self.line, start_col),
        )

    def _read_number(self) -> Token:
        start_col = self.col
        lexeme = ""

        # تشخیص باینری یا هگز (اولویت Longest Match)
        if self._current_char() == "0":
            if self._peek() in ("b", "B"):
                lexeme += self._advance() + self._advance()
                while self._current_char() in "01":
                    lexeme += self._advance()
                return Token(
                    TokenType.INT_LIT,
                    lexeme,
                    SourceLocation(self.file_name, self.line, start_col),
                )
            elif self._peek() in ("x", "X"):
                lexeme += self._advance() + self._advance()
                while self._current_char().isalnum():
                    lexeme += self._advance()
                return Token(
                    TokenType.INT_LIT,
                    lexeme,
                    SourceLocation(self.file_name, self.line, start_col),
                )

        # تشخیص اعداد اعشاری و علمی
        is_float = False
        while self._current_char().isdigit():
            lexeme += self._advance()

        if self._current_char() == ".":
            is_float = True
            lexeme += self._advance()
            while self._current_char().isdigit():
                lexeme += self._advance()

        if self._current_char() in ("e", "E"):
            is_float = True
            lexeme += self._advance()
            if self._current_char() in ("+", "-"):
                lexeme += self._advance()
            while self._current_char().isdigit():
                lexeme += self._advance()

        if self._current_char() in ("f", "F"):
            is_float = True
            lexeme += self._advance()

        token_type = TokenType.FLOAT_LIT if is_float else TokenType.INT_LIT
        return Token(
            token_type, lexeme, SourceLocation(self.file_name, self.line, start_col)
        )

    def _read_string(self) -> Token:
        start_col = self.col
        lexeme = '"'
        self._advance()  # رد کردن "
        while self.pos < self.length and self._current_char() != '"':
            if self._current_char() == "\\":  # هندل کردن escape
                lexeme += self._advance()
            lexeme += self._advance()

        if self.pos >= self.length:
            # خطای رشته تمام نشده
            return Token(
                TokenType.INVALID,
                lexeme,
                SourceLocation(self.file_name, self.line, start_col),
            )

        lexeme += self._advance()  # اضافه کردن " پایانی
        return Token(
            TokenType.STRING_LIT,
            lexeme,
            SourceLocation(self.file_name, self.line, start_col),
        )

    def _read_char(self) -> Token:
        start_col = self.col
        lexeme = "'"
        self._advance()
        if self._current_char() == "\\":
            lexeme += self._advance()
        lexeme += self._advance()
        if self._current_char() == "'":
            lexeme += self._advance()
            return Token(
                TokenType.CHAR_LIT,
                lexeme,
                SourceLocation(self.file_name, self.line, start_col),
            )
        else:
            return Token(
                TokenType.INVALID,
                lexeme,
                SourceLocation(self.file_name, self.line, start_col),
            )

    def _read_comment(self) -> str:
        """کامنت‌ها را می‌خواند و برمی‌گرداند (قرار نیست توکن شوند)"""
        lexeme = ""
        if self._current_char() == "/" and self._peek() == "/":
            while self._current_char() != "\n" and self.pos < self.length:
                lexeme += self._advance()
            return lexeme

        if self._current_char() == "/" and self._peek() == "*":
            self._advance()
            self._advance()
            while self.pos < self.length:
                if self._current_char() == "*" and self._peek() == "/":
                    self._advance()
                    self._advance()
                    return lexeme
                lexeme += self._advance()
            # خطای کامنت تمام نشده
            return lexeme

        return ""

    def _read_operator(self) -> Token:
        start_col = self.col
        char = self._current_char()

        # اولویت اول: عملگرهای دوکاراکتری که در گرامر داریم
        two_char_ops = {
            ">=": None,
            "<=": None,
            "==": None,
            "!=": None,
            "&&": None,
            "||": None,
            "->": None,
            "::": None,
            "++": None,
            "--": None,
            "+=": None,
            "-=": None,
            "*=": None,
            "/=": None,
        }

        # بررسی دو کاراکتر اول
        if self.pos + 1 < self.length:
            candidate = char + self.source[self.pos + 1]
            if candidate in two_char_ops:
                self._advance()  # مصرف کاراکتر اول (مثلاً >)
                self._advance()  # مصرف کاراکتر دوم (مثلاً =)
                return Token(
                    TokenType.OPERATOR,
                    candidate,  # مستقیماً از خود candidate استفاده می‌کنیم
                    SourceLocation(self.file_name, self.line, start_col),
                )

        # اگر دوکاراکتری نبود، تک‌کاراکتری
        lexeme = self._advance()  # اینجا advance کاراکتر را برمی‌گرداند و جلو می‌رود
        return Token(
            TokenType.OPERATOR,
            lexeme,
            SourceLocation(self.file_name, self.line, start_col),
        )

    def next_token(self) -> Token:
        self._skip_whitespace()

        if self.pos >= self.length:
            return Token(
                TokenType.EOF, "", SourceLocation(self.file_name, self.line, self.col)
            )

        char = self._current_char()

        # 1. Preprocessor Directives
        if char == "#":
            start_col = self.col
            lexeme = ""
            while self._current_char() != "\n" and self.pos < self.length:
                lexeme += self._advance()
            return Token(
                TokenType.DIRECTIVE,
                lexeme,
                SourceLocation(self.file_name, self.line, start_col),
            )

        # 2. Comments (Discard)
        if char == "/" and self._peek() in ("/", "*"):
            self._read_comment()
            return self.next_token()

        # 3. Identifiers & Keywords
        if char.isalpha() or char == "_":
            return self._read_identifier()

        # 4. Numbers
        if char.isdigit():
            return self._read_number()

        # 5. Strings
        if char == '"':
            return self._read_string()

        # 6. Characters
        if char == "'":
            return self._read_char()

        # 7. Operators
        if char in "+-*/%=<>!&|":
            return self._read_operator()

        # 8. Delimiters
        if char in "(){}[];,.":
            self._advance()
            return Token(
                TokenType.DELIMITER,
                char,
                SourceLocation(self.file_name, self.line, self.col - 1),
            )

        # 9. Invalid / Unrecognized
        self._advance()
        return Token(
            TokenType.INVALID,
            char,
            SourceLocation(self.file_name, self.line, self.col - 1),
        )

    def peek_token(self) -> Token:
        """برای نگاه به جلو (Lookahead) - برای پارسر بسیار مهم است"""
        current_pos = self.pos
        current_line = self.line
        current_col = self.col

        token = self.next_token()

        # بازگردانی وضعیت لکسر
        self.pos = current_pos
        self.line = current_line
        self.col = current_col
        return token
