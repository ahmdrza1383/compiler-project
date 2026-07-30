# Mini-C Lexical Analyzer (Lexer) Formal Specification

## 1. General Lexer Operation Rules
The Lexer must operate on the input source code as a stream of characters and transform it into a stream of Tokens. It must adhere to the following universal rules:

- **Maximal Munch (Longest Match):** At any given position, the Lexer must always consume the longest sequence of characters that matches a valid token pattern. (Example: Input `>=` must be tokenized as a single `GE` operator, not `>` followed by `=`).
- **Keyword Priority:** If an input string matches both a Keyword and an Identifier, the Keyword takes precedence. (Example: `if` must be tokenized as a `KEYWORD`, not an `IDENTIFIER`).
- **Whitespace Handling:** Whitespace (spaces, tabs, newlines) is recognized, but its location is tracked for error reporting, and the characters themselves are discarded (not passed to the parser).
- **Source Location Tracking:** Every emitted Token must store its absolute source location: `File Name`, `Line Number`, and `Column Number` for accurate error reporting and IDE features later on.
- **Error Recovery:** The Lexer must **never crash** on invalid input. Instead, it emits an `INVALID` token, records the offending character's location, advances one character, and continues scanning.

---

## 2. Token Category Specifications
The following table defines the exact Regular Expressions (Regex) and formal rules for every Token Category your Lexer must support.

| Token Category | Examples | Formal Regular Expression / Recognition Rule |
| :--- | :--- | :--- |
| **Keywords** | `if`, `else`, `while`, `for`, `return`, `int`, `float`, `char`, `void`, `struct` | **Finite set.** Checked before identifiers. Matched using exact string comparison.<br>Regex: `\b(if|else|while|for|return|int|float|char|void|struct)\b` |
| **Identifiers** | `myVar`, `_count`, `x1` | A letter or underscore, followed by any number of letters, digits, or underscores.<br>Regex: `[a-zA-Z_][a-zA-Z0-9_]*` |
| **Integer Literals** | `42` (Decimal)<br>`0xFF` (Hexadecimal)<br>`0b1010` (Binary) | Supports 3 bases. Must be checked in order (Binary → Hex → Decimal) to avoid conflicts.<br>Regex: `0[bB][01]+` \| `0[xX][0-9a-fA-F]+` \| `[0-9]+` |
| **Float Literals** | `3.14`<br>`1.0e-5` (Scientific)<br>`.5f` (Suffix) | Supports decimal points, scientific notation (`e`/`E`), and optional suffix (`f`/`F`).<br>Regex: `[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?[fF]?` \| `[0-9]+[eE][+-]?[0-9]+[fF]?` |
| **String Literals** | `"hello"`<br>`"hello\n"` | Quoted strings. Supports standard escape sequences (`\n`, `\t`, `\"`, `\\`).<br>Regex: `\"([^"\\]|\\.)*\"` |
| **Character Literals** | `'a'`<br>`'\t'` | Single character or escape sequence enclosed in single quotes.<br>Regex: `'([^'\\]|\\.)'` |
| **Operators** | `+`, `-`, `*`, `/`, `%`<br>`=`, `+=`, `-=`, `*=`, `/=`<br>`==`, `!=`, `<`, `>`, `<=`, `>=`<br>`&&`, `||`, `!`<br>`&`<br>`->`<br>`::` | **Longest Match is crucial here.** Multi-character operators must be matched before single-character ones.<br>Regex priority:<br>1. Multi-char: `<=|>=|==|!=|&&|\|\||\+=|-=|\*=|\/=|->|::`<br>2. Single-char: `[+\-*/%=<>!&|]` |
| **Delimiters (Punctuation)** | `(`, `)`, `{`, `}`, `[`, `]`, `;`, `,`, `.` | Structural punctuation strictly mapped to single-character matches.<br>Regex: `[(){}[\].,;:]` |
| **Single-line Comments** | `// text` | Matches from `//` to the end of the current line. **Discarded** (no token emitted to parser).<br>Regex: `//[^\n]*` |
| **Block Comments** | `/* text */` | Matches between `/*` and `*/`. **Discarded**.<br>**Nested support:** As a standard feature, use regex `\/\*([^*]|\*[^\/])*\*\/`. (For Bonus Points, implement a state-machine to support nesting). |
| **Whitespace** | spaces, tabs, newlines | Tracked for location, but **discarded**.<br>Regex: `[ \t\n\r]+` |
| **Preprocessor Directives** | `#include`, `#define` | Matches any line starting with `#` (excludes comments starting with `//` or `/*`). Treated as a single special Token class `DIRECTIVE` and passed to the parser (which will usually ignore it).<br>Regex: `#.*` |
| **Invalid Characters** | `@`, `$`, any other unrecognized symbol | Matches any single character not captured by the above rules.<br>Regex: `.`<br>*(Action: Emit an `INVALID` token with its location, then resume scanning from the next character.)* |

---

## 3. Lexical Error Handling (Required)
Your Lexer must implement the following specific error detection and recovery mechanisms, as per the PDF:

1. **Unterminated String Literals:**
   - *Detection:* If the Lexer encounters a starting quote `"` but reaches the End-Of-File (EOF) without finding a closing quote.
   - *Action:* Emit a `LEXICAL_ERROR` diagnostic with severity `Error`, file, line, column, and a message: "Unterminated string literal".
2. **Unterminated Block Comments:**
   - *Detection:* If the Lexer encounters `/*` but reaches EOF without finding `*/`.
   - *Action:* Emit a `LEXICAL_ERROR` diagnostic: "Unterminated block comment".
3. **Invalid / Unrecognized Character:**
   - *Detection:* Any character not matching the defined token regexes.
   - *Action:* Emit an `INVALID` token with the `lexeme` set to the offending character, record its exact location, emit a diagnostic ("Unrecognized character '@'"), and **advance exactly one character** to resume scanning.

---

## 4. Lexer Interface (Software Architecture)
To connect this to your Parser, the Lexer must expose the following API:

- **`Token nextToken()`**: Reads the next sequence of characters from the input stream and returns the next Token object. 
- **`Token peekToken()`**: Returns the next Token without advancing the input stream (allows the Parser to look ahead 1 token for LL(1) decisions).
- **`Token` Structure**: Must contain the following fields:
  - `TokenType type` (Enum: `KEYWORD`, `IDENTIFIER`, `INT_LIT`, `FLOAT_LIT`, `STRING_LIT`, `CHAR_LIT`, `OPERATOR`, `DELIMITER`, `DIRECTIVE`, `INVALID`, `EOF`).
  - `std::string lexeme` (The exact matched string).
  - `SourceLocation location` (Struct with `file_name`, `line`, `column`).
