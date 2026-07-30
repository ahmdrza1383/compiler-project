# Formal Specification for the Mini-C Lexical Analyzer (Lexer)

## 1. General Lexer Operation Rules
The Lexer operates on a source code character stream and transforms it into a stream of Tokens for the Parser. It must strictly adhere to the following universal rules:

- **Maximal Munch (Longest Match):** At any given position, the Lexer must always consume the longest sequence of characters that matches a valid token pattern. *(Example: Input `>=` must be tokenized as a single `GE` operator, never as `>` followed by `=`).*
- **Keyword Priority:** If an input string matches both a reserved Keyword and an Identifier, the Keyword takes absolute precedence. *(Example: `if` must be tokenized as `KEYWORD`, never as `IDENTIFIER`).*
- **Discarding of Whitespace and Comments:** Whitespace (` `, `\t`, `\n`, `\r`), single-line comments (`//`), and block comments (`/* */`) are lexically recognized but fully discarded. No tokens are emitted for them to the Parser.
- **Source Location Tracking:** Every emitted Token must store its exact source location: `File Name`, `Line Number`, and `Column Number`. This is critical for later error reporting and IDE features.
- **Error Recovery:** The Lexer **must never crash** on invalid input. Instead, it emits an `INVALID` token, records the offending character's exact location, advances exactly one character past the error, and immediately resumes scanning.

---

## 2. Complete Token Category Specifications (Regex Table)
The table below defines the exact Regular Expressions (Regex) and recognition rules for every Token Category required by the Mini-C grammar.

| Token Category | Examples | Formal Regular Expression / Recognition Rule |
| :--- | :--- | :--- |
| **Keywords** | `if`, `else`, `while`, `for`, `return`<br>`int`, `float`, `double`, `char`, `void`<br>`struct`, `break`, `continue` | **Finite set.** Checked strictly before identifiers to enforce priority.<br>Regex: `\b(if|else|while|for|return|int|float|double|char|void|struct|break|continue)\b` |
| **Identifiers** | `myVar`, `_count`, `x1` | A letter or underscore, followed by any number of letters, digits, or underscores.<br>Regex: `[a-zA-Z_][a-zA-Z0-9_]*` |
| **Integer Literals** | `42` (Decimal)<br>`0xFF` (Hexadecimal)<br>`0b1010` (Binary) | Supports 3 bases. **Order matters**: Binary → Hex → Decimal.<br>Regex: `0[bB][01]+` \| `0[xX][0-9a-fA-F]+` \| `[0-9]+` |
| **Float Literals** | `3.14`<br>`1.0e-5` (Scientific)<br>`.5f` (Suffix) | Supports decimal points, scientific notation (`e`/`E`), and optional suffixes (`f`/`F`).<br>Regex: `[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?[fF]?` \| `[0-9]+[eE][+-]?[0-9]+[fF]?` |
| **String Literals** | `"hello"`, `"hello\n"` | Quoted strings. Supports standard escape sequences (`\n`, `\t`, `\"`, `\\`).<br>Regex: `\"([^"\\]|\\.)*\"` |
| **Character Literals** | `'a'`, `'\t'` | Single character or escape sequence enclosed in single quotes.<br>Regex: `'([^'\\]|\\.)'` |
| **Multi-character Operators** | `<=`, `>=`, `==`, `!=`, `&&`, `\|\|`, `+=`, `-=`, `*=`, `/=`, `->`, `::`, `++`, `--` | **Crucial for Longest Match.** These must be checked before single-character operators.<br>Regex: `<=|>=|==|!=|&&|\|\||\+=|-=|\*=|\/=|->|::|\+\+|--` |
| **Single-character Operators** | `+`, `-`, `*`, `/`, `%`, `=`, `<`, `>`, `!`, `&`, `\|` | Checked only if no multi-character operator matched.<br>Regex: `[+\-*/%=<>!&|]` |
| **Delimiters (Punctuation)** | `(`, `)`, `{`, `}`, `[`, `]`, `;`, `,`, `.` | Structural punctuation strictly mapped to single-character matches.<br>Regex: `[(){}[\].,;:]` |
| **Single-line Comments** | `// text` | Matches from `//` to the end of the line. **Discarded.**<br>Regex: `//[^\n]*` |
| **Block Comments** | `/* text */` | Matches between `/*` and `*/`. **Discarded.**<br>Standard Regex: `\/\*([^*]|\*[^\/])*\*\/` |
| **Preprocessor Directives** | `#include`, `#define` | Matches entire lines starting with `#` (excluding comments). Emitted as a special `DIRECTIVE` token which the Parser will safely ignore at the top level.<br>Regex: `#.*` |
| **Whitespace** | Spaces, Tabs, Newlines | Tracked for line/column counts, but **discarded**.<br>Regex: `[ \t\n\r]+` |
| **Invalid Characters** | `@`, `$`, any other unrecognized symbol | Fallback rule. Matches any single character not captured by the above rules.<br>Regex: `.` <br>*(Action: Emit an `INVALID` token, record its exact location, and advance one character to resume).* |

---

## 3. Mandatory Lexical Error Handling
The Lexer must implement the following specific error detection and reporting mechanisms, as strictly required by the project document:

1. **Unterminated String Literals:**
   - *Detection:* The Lexer encounters a starting quote `"`, but reaches the End-Of-File (EOF) without finding a closing quote.
   - *Action:* Emit a `LEXICAL_ERROR` diagnostic with severity `Error`, file location, and message: *"Unterminated string literal"*.
2. **Unterminated Block Comments:**
   - *Detection:* The Lexer encounters `/*` but reaches EOF without finding the closing `*/`.
   - *Action:* Emit a `LEXICAL_ERROR` diagnostic: *"Unterminated block comment"*.
3. **Unrecognized / Invalid Character:**
   - *Detection:* Any character not matching the defined token regexes.
   - *Action:* Emit an `INVALID` token where `lexeme` is the offending character, record its exact location, emit a diagnostic (*"Unrecognized character '@'"*), advance **exactly one character** past the error, and immediately resume scanning.

---

## 4. Lexer API Interface (For Phase 1 Implementation)
To seamlessly connect your Lexer to the Recursive Descent Parser, the Lexer must expose the following clear interface:

- **`Token nextToken()`**: Consumes the next sequence of characters from the input stream and returns the next `Token` object, advancing the internal stream pointer.
- **`Token peekToken()`**: Returns the next `Token` object *without* advancing the input stream. This allows the Parser to perform 1-token Lookahead, which is strictly required for our LL(1) decision-making (e.g., distinguishing `struct_prefix` from `non_struct_decl`).
- **`bool hasError()`**: Returns `true` if any lexical error was recorded, allowing the driver to list all errors at the end.

The **`Token` structure** must contain the following mandatory fields:
- `TokenType type`: An `enum` with values: `KEYWORD`, `IDENTIFIER`, `INT_LIT`, `FLOAT_LIT`, `STRING_LIT`, `CHAR_LIT`, `OPERATOR`, `DELIMITER`, `DIRECTIVE`, `INVALID`, `EOF`.
- `std::string lexeme`: The exact character sequence matched from the source code.
- `SourceLocation location`: A struct containing `file_name`, `line`, and `column`.
