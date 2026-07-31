from .token import Token, TokenType, SourceLocation
from .error_reporter import ErrorReporter, Severity


class Lexer:
    def __init__(
        self,
        source_code: str,
        file_name: str = "<stdin>",
        reporter: ErrorReporter = None,
    ):
        self.source = source_code
        self.file_name = file_name
        self.pos = 0
        self.line = 1
        self.col = 1
        self.length = len(source_code)
        self.reporter = reporter if reporter else ErrorReporter()

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

    def _add_error(self, message: str, line: int, column: int, length: int):
        self.reporter.report("Lexer", Severity.ERROR, message, line, column, length)

    def has_errors(self) -> bool:
        return self.reporter.has_errors()

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
                while self._current_char() in "0123456789abcdefABCDEF":
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
        self._advance()
        while self.pos < self.length and self._current_char() != '"':
            if self._current_char() == "\\":
                lexeme += self._advance()
            lexeme += self._advance()

        if self.pos >= self.length:
            self._add_error(
                "Unterminated string literal", self.line, start_col, len(lexeme)
            )
            return Token(
                TokenType.INVALID,
                lexeme,
                SourceLocation(self.file_name, self.line, start_col),
            )

        lexeme += self._advance()
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
            self._add_error(
                "Unterminated character literal", self.line, start_col, len(lexeme)
            )
            return Token(
                TokenType.INVALID,
                lexeme,
                SourceLocation(self.file_name, self.line, start_col),
            )

    def _read_comment(self) -> bool:
        """خواندن کامنت و بازگرداندن True اگر کامل بسته شد، در غیر این صورت False"""
        if self._current_char() == "/" and self._peek() == "/":
            while self._current_char() != "\n" and self.pos < self.length:
                self._advance()
            return True

        if self._current_char() == "/" and self._peek() == "*":
            self._advance()
            self._advance()
            while self.pos < self.length:
                if self._current_char() == "*" and self._peek() == "/":
                    self._advance()
                    self._advance()
                    return True
                self._advance()
            return False

        return True

    def _read_operator(self) -> Token:
        start_col = self.col
        char = self._current_char()

        two_char_ops = {
            ">=": None,
            "<=": None,
            "==": None,
            "!=": None,
            "&&": None,
            "||": None,
            "->": None,
            "++": None,
            "--": None,
            "+=": None,
            "-=": None,
            "*=": None,
            "/=": None,
            "%=": None,
        }

        if self.pos + 1 < self.length:
            candidate = char + self.source[self.pos + 1]
            if candidate in two_char_ops:
                self._advance()
                self._advance()
                return Token(
                    TokenType.OPERATOR,
                    candidate,
                    SourceLocation(self.file_name, self.line, start_col),
                )

        lexeme = self._advance()
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
            start_pos = self.pos
            start_line = self.line
            start_col = self.col
            closed = self._read_comment()
            if not closed:
                length = self.pos - start_pos
                self._add_error(
                    "Unterminated block comment", start_line, start_col, length
                )
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
        if char in "(){}[];,.:":
            start_col = self.col
            self._advance()
            return Token(
                TokenType.DELIMITER,
                char,
                SourceLocation(self.file_name, self.line, start_col),
            )

        # 9. Invalid / Unrecognized
        start_col = self.col
        char = self._advance()
        self._add_error(f"Unrecognized character '{char}'", self.line, start_col, 1)
        return Token(
            TokenType.INVALID,
            char,
            SourceLocation(self.file_name, self.line, start_col),
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
