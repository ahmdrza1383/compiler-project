from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    EOF = "EOF"
    INVALID = "INVALID"
    DIRECTIVE = "DIRECTIVE"

    IDENTIFIER = "IDENTIFIER"
    INT_LIT = "INT_LIT"
    FLOAT_LIT = "FLOAT_LIT"
    STRING_LIT = "STRING_LIT"
    CHAR_LIT = "CHAR_LIT"

    KEYWORD = "KEYWORD"

    OPERATOR = "OPERATOR"
    DELIMITER = "DELIMITER"


@dataclass
class SourceLocation:
    file_name: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.file_name}:{self.line}:{self.column}"


@dataclass
class Token:
    type: TokenType
    lexeme: str
    location: SourceLocation

    def to_dict(self) -> dict:
        """تبدیل توکن به دیکشنری برای ذخیره در فایل JSON"""
        return {
            "type": self.type.value,
            "lexeme": self.lexeme,
            "location": {
                "file": self.location.file_name,
                "line": self.location.line,
                "col": self.location.column,
            },
        }
