# Formal Specification for the Mini-C Lexical Analyzer (Lexer)

## 1. General Lexer Operation Rules
The Lexer operates on a character stream and produces a token stream. It must strictly adhere to these rules:

- **Maximal Munch (Longest Match):** Always consume the longest possible sequence of characters matching a valid token pattern. *(e.g., `>=` becomes a single `GE` operator, not `>` then `=`).*
- **Keyword Priority:** Keywords take precedence over Identifiers. *(e.g., `if` is always `KEYWORD`, never `IDENTIFIER`).*
- **Whitespace and Comment Discarding:** Whitespace (` `, `\t`, `\n`, `\r`), single-line comments (`//`), and block comments (`/* */`) are lexically recognized but fully discarded. No tokens are passed to the Parser.
- **Source Location Tracking:** Every Token stores `File Name`, `Line Number`, and `Column Number` for error reporting.
- **Error Recovery:** The Lexer **never crashes**. On invalid input, it emits an `INVALID` token, records the location, advances one character, and resumes scanning.

---

## 2. Complete Token Category Specifications (Regex Table)

| Token Category | Examples | Formal Regular Expression / Recognition Rule |
| :--- | :--- | :--- |
| **Keywords** | `if`, `else`, `while`, `for`, `return`, `int`, `float`, `double`, `char`, `void`, `struct`, `break`, `continue` | **Finite set** (checked before identifiers).<br>Regex: `\b(if|else|while|for|return|int|float|double|char|void|struct|break|continue)\b` |
| **Identifiers** | `myVar`, `_count`, `x1` | Letter/underscore, followed by letters, digits, or underscores.<br>Regex: `[a-zA-Z_][a-zA-Z0-9_]*` |
| **Integer Literals** | `42` (Decimal), `0xFF` (Hex), `0b1010` (Binary) | Supports Decimal, Hexadecimal, Binary.<br>Regex: `0[bB][01]+` \| `0[xX][0-9a-fA-F]+` \| `[0-9]+` |
| **Float Literals** | `3.14`, `1.0e-5` (Scientific), `.5f` | Supports scientific notation and suffixes (`f`/`F`).<br>Regex: `[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?[fF]?` \| `[0-9]+[eE][+-]?[0-9]+[fF]?` |
| **String Literals** | `"hello"`, `"hello\n"` | Supports escape sequences (`\n`, `\t`, `\"`, `\\`).<br>Regex: `\"([^"\\]|\\.)*\"` |
| **Character Literals** | `'a'`, `'\t'` | Supports escaped characters.<br>Regex: `'([^'\\]|\\.)'` |
| **Multi-character Operators** | `<=`, `>=`, `==`, `!=`, `&&`, `\|\|`, `+=`, `-=`, `*=`, `/=`, `->`, `::`, `++`, `--` | **Longest match priority**.<br>Regex: `<=|>=|==|!=|&&|\|\||\+=|-=|\*=|\/=|->|::|\+\+|--` |
| **Single-character Operators** | `+`, `-`, `*`, `/`, `%`, `=`, `<`, `>`, `!`, `&`, `\|` | Matched only after multi-character operators fail.<br>Regex: `[+\-*/%=<>!&|]` |
| **Delimiters (Punctuation)** | `(`, `)`, `{`, `}`, `[`, `]`, `;`, `,`, `.` | Structural punctuation.<br>Regex: `[(){}[\].,;:]` |
| **Single-line Comments** | `// text` | Discarded.<br>Regex: `//[^\n]*` |
| **Block Comments** | `/* text */` | Discarded.<br>Regex: `\/\*([^*]|\*[^\/])*\*\/` |
| **Preprocessor Directives** | `#include`, `#define` | Emitted as `DIRECTIVE` and ignored by Parser.<br>Regex: `#.*` |
| **Whitespace** | Spaces, Tabs, Newlines | Tracked for location, **discarded**.<br>Regex: `[ \t\n\r]+` |
| **Invalid Characters** | `@`, `$` | Fallback rule. Emit `INVALID`, record location, advance 1 char.<br>Regex: `.` |

---

## 3. Mandatory Lexical Error Handling

- **Unterminated String Literal:** If `"` starts but EOF is reached before closing, emit `"Unterminated string literal"`.
- **Unterminated Block Comment:** If `/*` starts but EOF is reached before `*/`, emit `"Unterminated block comment"`.
- **Invalid Character:** Emit `"Unrecognized character 'X'"` and resume.

---

## 4. Lexer API Interface (For Phase 1 Implementation)

- **`Token nextToken()`**: Consumes input and returns the next `Token`. Advances the stream pointer.
- **`Token peekToken()`**: Returns the next `Token` **without** advancing the stream. (Crucial for LL(1) lookahead decisions).
- **`bool hasError()`**: Returns `true` if any lexical error was recorded.

**`Token` structure** must contain:
- `TokenType type`: Enum (`KEYWORD`, `IDENTIFIER`, `INT_LIT`, `FLOAT_LIT`, `STRING_LIT`, `CHAR_LIT`, `OPERATOR`, `DELIMITER`, `DIRECTIVE`, `INVALID`, `EOF`).
- `std::string lexeme`: The exact matched substring.
- `SourceLocation location`: Struct with `file_name`, `line`, `column`.

