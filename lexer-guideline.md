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
| **Keywords** | `if`, `else`, `while`, `for`, `return`, `int`, `float`, `double`, `char`, `void`, `struct`, `break`, `continue` | **Finite set.** Checked before identifiers.<br>Regex: `\b(if|else|while|for|return|int|float|double|char|void|struct|break|continue)\b` |
| **Identifiers** | `myVar`, `_count` | Regex: `[a-zA-Z_][a-zA-Z0-9_]*` |
| **Integer Literals** | `42` (Decimal), `0xFF` (Hex), `0b1010` (Binary) | Regex: `0[bB][01]+` \| `0[xX][0-9a-fA-F]+` \| `[0-9]+` (Priority: Binary -> Hex -> Decimal) |
| **Float Literals** | `3.14`, `1.0e-5`, `.5f` | Regex: `[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?[fF]?` \| `[0-9]+[eE][+-]?[0-9]+[fF]?` |
| **String Literals** | `"hello"`, `"hello\n"` | Regex: `\"([^"\\]|\\.)*\"` |
| **Character Literals** | `'a'`, `'\t'` | Regex: `'([^'\\]|\\.)'` |
| **Operators** | `+`, `-`, `*`, `/`, `%`, `=`, `+=`, `-=`, `*=`, `/=`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `&&`, `||`, `!`, `&`, `->`, `::`, `++`, `--` | **Longest Match priority:**<br>1. Multi-char: `<=|>=|==|!=|&&|\|\||\+=|-=|\*=|\/=|->|::|\+\+|--`<br>2. Single-char: `[+\-*/%=<>!&|]` |
| **Delimiters** | `(`, `)`, `{`, `}`, `[`, `]`, `;`, `,`, `.` | Regex: `[(){}[\].,;:]` |
| **Single-line Comments** | `// text` | Regex: `//[^\n]*` (Discarded) |
| **Block Comments** | `/* text */` | Regex: `\/\*([^*]|\*[^\/])*\*\/` (Discarded) |
| **Preprocessor Directives** | `#include`, `#define` | Regex: `#.*` (Tokenized as `DIRECTIVE` and ignored by Parser) |
| **Whitespace** | `\t`, `\n`, ` `, `\r` | Regex: `[ \t\n\r]+` (Discarded, Location tracked) |
| **Invalid Characters** | `@`, `$`, ... | Regex: `.` (Emit `INVALID`, record location, advance 1 char) |

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