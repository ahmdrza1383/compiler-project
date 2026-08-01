# 📋 مستند جامع و متن ارائه پروژه نهایی درس طراحی کامپایلرها

## دانشگاه صنعتی شریف - دانشکده مهندسی کامپیوتر
### ترم بهار ۱۴۰۴-۱۴۰۵ | استاد: دکتر علاییان | مسئول درس: علیرضا قربانی

---

## 🎯 مقدمه و اهداف پروژه

این پروژه یک **سیستم کامل تحلیل کد با قابلیت‌های IDE** برای زبان Mini-C است که دقیقاً مطابق با مشخصات پروژه پایانی درس طراحی کامپایلرها پیاده‌سازی شده است. سیستم ما سه فاز اصلی را پوشش می‌دهد:

1. **فاز بصری (Visual):** هایلایتینگ سینتکس با رنگ‌بندی معنایی
2. **فاز معنایی (Semantic):** درک اسکوپ، انواع داده‌ها، و جدول نمادها
3. **فاز ساختاری (Structural):** تحلیل‌های برنامه‌ای، CFG، Call Graph، و قابلیت‌های Refactoring

### 🔗 اتصال به مفاهیم درس

این پروژه در تقاطع سه حوزه دانش اصلی این درس قرار دارد:

| حوزه دانش | مفاهیم پیاده‌سازی شده |
|-----------|----------------------|
| **نظریه زبان‌های صوری** | زبان‌های منظم، گرامرهای مستقل از متن، اتوماتای پشته‌ای |
| **طراحی Front-End کامپایلر** | Lexing, Parsing, AST, Symbol Tables, Type Systems |
| **تحلیل برنامه** | Control Flow Graphs, Call Graphs, Data-flow Analysis, تشخیص خطاهای ایستا |

---

## 🔄 روند کلی کار (System Pipeline)

```
┌─────────────┐     ┌──────────┐     ┌─────────┐     ┌──────────────────┐
│ Source Code │ ──→ │  Lexer   │ ──→ │ Parser  │ ──→ │ Semantic Analyzer│
│   (test.c)  │     │ (DFA-based)│   |Recursive│     │  (Symbol Table + |
└─────────────┘     └──────────┘     │ Descent │     │  Type Checker)   │
                                     └─────────┘     └──────────────────┘
                                             ↓                    ↓
                                    ┌─────────────────────────────────┐
                                    │      AST + Annotated AST        │
                                    └─────────────────────────────────┘
                                              ↓
                    ┌─────────────────────────┼─────────────────────────┐
                    ↓                         ↓                         ↓
           ┌────────────────┐      ┌──────────────────┐      ┌─────────────────┐
           │ Syntax         │      │ Program Analysis │      │ Intellisense    │
           │ Highlighter    │      │ (CFG + Call Graph│      │ Engine          │
           │ (Phase 1)      │      │  + Data Flow)    │      │ (Phase 2)       │
           └────────────────┘      │  (Phase 3)       │      └─────────────────┘
                                   └──────────────────┘
```

### 📊 گردش داده‌ها

1. **Lexer:** تبدیل جریان کاراکتر به توکن‌های تایپ‌دار (بر پایه DFA)
2. **Parser:** ساخت CST/AST طبق گرامر EBNF
3. **Semantic Analyzer:**
   - ساخت Symbol Table با دو پاس (Declaration Scan + Resolution)
   - حل نام‌ها (Name Binding)
   - بررسی نوع (Type Checking)
4. **Syntax Highlighter:** پیمایش AST annotate شده و نگاشت به رنگ‌ها
5. **Intellisense Engine:** کوئری از Symbol Table و AST برای تکمیل کد
6. **Program Analyzer:** ساخت CFG، Call Graph، و پیاده‌سازی ناوبری و Refactoring

---

## 📁 ساختار پروژه و توضیح فایل‌به‌فایل

### بخش ۱: هسته کامپایلر (Compiler Core)

#### 🔹 `src/token.py` (۴۸ خط)
**وظیفه:** تعریف ساختارهای پایه برای توکن‌ها طبق Section 4.2 داکیومنت

**کلاس‌های اصلی:**
- `TokenType`: Enum شامل انواع توکن (KEYWORD, IDENTIFIER, INT_LIT, FLOAT_LIT, STRING_LIT, CHAR_LIT, OPERATOR, DELIMITER, COMMENT, WHITESPACE, DIRECTIVE, INVALID)
- `SourceLocation`: ذخیره موقعیت مکانی (file_name, line_number, column_number) - ضروری برای گزارش خطا
- `Token`: نگهداری type, lexeme, location

**ارتباط با داکیومنت:** پیاده‌سازی الزامات Section 4.2.1 برای دسته‌بندی توکن‌ها

---

#### 🔹 `src/lexer.py` (۳۷۰ خط)
**وظیفه:** تجزیه کد منبع به توکن‌ها (Lexical Analysis) - Section 4.2

**پشتیبانی از تمام دسته‌های توکن مورد نیاز:**
| دسته | مثال‌ها | توصیف صوری |
|------|---------|------------|
| Keywords | if, while, return, int, float, struct | مجموعه متناهی، چک قبل از identifier |
| Identifiers | myVar, _count, x1 | `[a-zA-Z_][a-zA-Z0-9_]*` |
| Integer literals | 42, 0xFF, 0b1010 | دهدهی / هگز / باینری |
| Float literals | 3.14, 1.0e-5, .5f | با exponent و suffix اختیاری |
| String literals | "hello\n" | Quoted با پشتیبانی از escape |
| Character literals | 'a', '\t' | تک کاراکتر یا escape |
| Operators | +, ->, <=, :: | مجموعه خاص زبان |
| Delimiters | {, (, ;, , | علائم ساختاری |
| Comments | // text, /* text */ | Single-line و Block |
| Preprocessor | #include, #define | برای C/C++ |

**قوانین Longest-Match و Priority (Section 4.2.2):**
1. **Longest match (maximal munch):** همیشه بلندترین توکن ممکن مصرف شود (مثال: `<=` یک توکن است نه `<` و `=`)
2. **Priority:** کلیدواژه‌ها بر identifier اولویت دارند (`while` → KEYWORD نه IDENT)

**مدیریت خطا (Section 4.2.3):**
- تولید `INVALID` token برای کاراکترهای ناشناخته
- بازیابی با پیشروی past offending character
- تشخیص رشته‌ها و کامنت‌های ناتمام

**متدهای کلیدی:**
- `next_token()`: تولید توکن بعدی با شبیه‌سازی DFA
- `_read_identifier()`, `_read_number()`, `_read_string()`: توابع کمکی
- `peek_token()`: lookahead بدون مصرف توکن

---

#### 🔹 `grammer.txt` (گرامر EBNF)
**وظیفه:** مشخصات کامل گرامر زبان Mini-C طبق Section 4.3.1

**بخش‌های اصلی گرامر:**
```ebnf
program ::= declaration* EOF
declaration ::= function_decl | var_decl | struct_decl
function_decl ::= type_spec IDENT '(' param_list? ')' block
param_list ::= param (',' param)*
param ::= type_spec IDENT
type_spec ::= ('int'|'float'|'char'|'void'|'double') '*'*
block ::= '{' statement* '}'
statement ::= if_stmt | while_stmt | for_stmt | return_stmt
            | expr_stmt | block | var_decl | break_stmt | continue_stmt
if_stmt ::= 'if' '(' expr ')' statement ('else' statement)?
while_stmt ::= 'while' '(' expr ')' statement
for_stmt ::= 'for' '(' expr_stmt expr_stmt expr? ')' statement
return_stmt ::= 'return' expr? ';'
expr ::= assignment
assignment ::= IDENT ('='|'+='|'-='|'*=') assignment | logical_or
logical_or ::= logical_and ('||' logical_and)*
logical_and ::= equality ('&&' equality)*
equality ::= relational (('=='|'!=') relational)*
relational ::= additive (('<'|'>'|'<='|'>=') additive)*
additive ::= multiplicative (('+'|'-') multiplicative)*
multiplicative ::= unary (('*'|'/'|'%') unary)*
unary ::= ('-'|'!'|'&'|'*') unary | postfix
postfix ::= primary ('[' expr ']' | '(' arg_list? ')' | '.' IDENT | '->' IDENT)*
primary ::= INT | FLOAT | STRING | CHAR | IDENT | '(' expr ')'
```

**حذف Left Recursion:** گرامر برای Recursive Descent مناسب است (بدون left recursion)

---

#### 🔹 `src/parser.py` (۵۴۷ خط)
**وظیفه:** ساخت AST از جریان توکن‌ها طبق گرامر EBNF - Section 4.3

**استراتژی Parsing:** Recursive Descent Parser (LL) با Panic-Mode Error Recovery

**پیاده‌سازی گرامر:**
- هر non-terminal به یک متد تبدیل شده است
- `parse_program()`, `parse_declaration()`, `parse_statement()`, `parse_expression()`
- مدیریت operator precedence با سلسله مراتب متدها

**مدیریت خطا (Section 9):**
- `error()`: ثبت خطا در ErrorReporter بدون crash کردن
- `synchronize()`: پرش تا نقطه امن (sync tokens: `;`, `}`, `if`, `while`) برای ادامه parsing
- سیستم باید روی کدهای erroneous هم خروجی تولید کند

**خروجی:** یک `Program` node که ریشه AST است

---

#### 🔹 `src/ast_node.py` (۱۶۸ خط)
**وظیفه:** تعریف کلاس‌های گره‌های AST - Section 4.3.2

**انواع گره‌ها:**
| نوع | کلاس‌ها |
|-----|---------|
| **برگی** | `Identifier`, `Literal`, `TypeSpecifier` |
| **ساختاری** | `Program`, `Block`, `FunctionDef`, `FunctionDecl`, `StructDef`, `VarDecl` |
| **کنترلی** | `IfStmt`, `WhileStmt`, `ForStmt`, `ReturnStmt`, `BreakStmt`, `ContinueStmt` |
| **عبارتی** | `CallExpr`, `BinaryExpr`, `UnaryExpr`, `ArrayAccess`, `MemberAccess` |

**ویژگی فنی:** ارث‌بری از `NodeMixin` کتابخانه anytree برای مدیریت خودکار ساختار درختی

---

#### 🔹 `src/error_reporter.py` (۷۵ خط)
**وظیفه:** مدیریت متمرکز خطاها طبق Section 4.2.3 و Section 9

**کلاس‌ها:**
- `Severity`: Enum (ERROR, WARNING, INFO)
- `Diagnostic`: اطلاعات کامل خطا (phase, message, location, length)
- `ErrorReporter`: جمع‌آوری و خروجی JSON/TXT

**الزام داکیومنت:** سیستم نباید crash کند، باید خطاها را گزارش دهد و به پردازش ادامه دهد

---

### بخش ۲: تحلیل معنایی (Semantic Analysis)

#### 🔹 `src/symbol_table.py` (۲۰۵ خط)
**وظیفه:** پیاده‌سازی ساختار داده Symbol Table طبق Section 5.1

**کلاس‌های اصلی:**
- `Symbol`: name, type, scope_level, definition_location, references[], signature
- `Scope`: ساختار درختی parent-child برای سلسله مراتب اسکوپ
- `SymbolTable`: مدیریت global scope و current scope

**عملیات کلیدی:**
- `define()`: تعریف نماد جدید در scope جاری
- `resolve()`: جستجو از inner به outer (section 5.1.1)
- `enter_scope()`, `exit_scope()`: مدیریت سلسله مراتب

---

#### 🔹 `src/symbol_table_builder.py` (۴۵۱ خط)
**وظیفه:** ساخت Symbol Table از AST در دو پاس - Section 5.1.2

**Pass 1: Declaration Scan**
- اسکن تمام declarationهای سراسری (functions, structs, global vars)
- ثبت signature توابع و fieldهای struct
- تشخیص redefinition conflicts

**Pass 2: Resolution**
- ورود به scope توابع و بلوک‌ها
- ثبت پارامترها و متغیرهای محلی
- حل ارجاعات Identifierها
- تشخیص Shadowing و undefined variables

**Built-in Functions:** پشتیبانی از printf, scanf, malloc, free

---

#### 🔹 `src/type_checker.py` (۶۲۳ خط)
**وظیفه:** بررسی سازگاری انواع داده‌ها - Section 5.2

**سیستم انواع (Type System):**
- `PrimitiveType`: int, float, double, char, void
- `PointerType`: pointer به هر نوع
- `ArrayType`: آرایه با اندازه مشخص/نامشخص
- `StructType`: انواع ساختاری

**قوانین Type Checking:**
| عملیات | قانون بررسی |
|--------|-------------|
| Assignment | سازگاری LHS و RHS |
| Binary Operators | فقط روی numeric types |
| Logical Operators | روی boolean/numeric |
| Function Call | تطابق تعداد و نوع آرگومان‌ها |
| Member Access | وجود field در struct |
| Return | تطابق با return type تابع |

**خروجی:** لیست type errors و warnings

---

### بخش ۳: تحلیل برنامه (Program Analysis) - Phase 3

#### 🔹 `src/graphs.py` (۲۳۷ خط)
**وظیفه:** ساخت CFG و Call Graph - Section 6.1 و 6.2

**Control Flow Graph (CFG):**
- `BasicBlock`: maximal sequence بدون branch، یک entry، حداکثر دو successor
- `CFGBuilder`: الگوریتم DFS برای ساخت CFG از AST
- یال‌ها: مسیرهای اجرای ممکن (true/false branches, loop back-edges, exits)

**قوانین ساخت CFG:**
| Statement | ساختار CFG |
|-----------|------------|
| IfStmt | ۳ بلوک (condition, then, merge/else) |
| WhileStmt | condition, body, exit با back-edge |
| ForStmt | ۴ بلوک (init, condition, body, step) |
| Return/Break/Continue | اتصال به exit یا loop boundaries |

**Call Graph:**
- Nodes: تمام توابع برنامه
- Edges: f→g اگر f تابع g را صدا بزند
- Resolution با استفاده از Symbol Table

---

#### 🔹 `src/data_flow.py` (۱۴۵ خط)
**وظیفه:** تحلیل جریان داده - Section 6.1.1 و 6.5

**تحلیل‌های پیاده‌سازی شده:**

1. **Definite Assignment Analysis (Forward May-Analysis)**
   - لاتییس: ⟨2^Vars, ⊇⟩
   - بررسی مقداردهی قطعی قبل از استفاده

2. **Live Variable Analysis (Backward May-Analysis)**
   - لاتییس: ⟨2^Vars, ⊆⟩
   - متغیر live اگر مقدارش در آینده استفاده شود

3. **Unreachable Code Detection**
   - بلوک بدون incoming edge (غیر از ENTRY)
   - کد پس از return/break/continue غیرشرطی

4. **Dead Code Categories (Section 6.5):**
   - Unreachable functions (از main قابل دستیابی نیستند)
   - Unreachable basic blocks
   - Post-jump statements
   - Unused variables
   - Dead assignments (مقدار overwrite قبل از read)

---

### بخش ۴: قابلیت‌های IDE

#### 🔹 `src/highlighter.py` (۴۱۹ خط)
**وظیفه:** Syntax Highlighting معنایی - Section 4

**رنگ‌بندی:**
| Category | Color |
|----------|-------|
| Keywords | Blue |
| Types | Green |
| Functions | Gold |
| Variables | White |
| Numbers | Orange |
| Strings | Light Green |
| Operators | Gray |
| Comments | Dark Gray |
| Errors | Red |

**روش کار:**
1. استخراج توکن‌ها از Lexer
2. غنی‌سازی با اطلاعات AST (تشخیص function names, struct names)
3. اولویت‌بندی (errors > AST info > tokens)
4. خروجی ANSI (terminal) و HTML/CSS (browser)

---

#### 🔹 `src/navigation.py` (۱۴۰ خط)
**وظیفه:** Go-to-Definition و Find-All-References - Section 6.3

**قابلیت‌ها:**
1. **Go-to-Definition:** بازگشت exact location تعریف نماد
2. **Find All References:** لیست تمام read/writeهای نماد
3. **Hover Information:** نمایش type signature, enclosing scope, documentation

**فرمت خروجی (JSON):**
```json
{
  "symbol": "factorial",
  "kind": "function",
  "type": "(int) -> int",
  "defined_at": {"file": "main.c", "line": 1, "col": 5},
  "references": [
    {"file": "main.c", "line": 15, "col": 12}
  ]
}
```

---

#### 🔹 `src/refactoring.py` (۷۵ خط)
**وظیفه:** Safe Rename Refactoring - Section 6.4

**الگوریسم Semantics-Preserving:**
1. پیدا کردن symbol در location مشخص
2. Conflict check: عدم تداخل نام جدید در same scope
3. Shadow check: جلوگیری از shadowing ناخواسته
4. Unified diff production
5. Atomic apply: همه یا هیچ

**الزام داکیومنت:** Rename باید scope-aware باشد، نه text-substitution ساده

---

#### 🔹 `src/auto_completer.py` (۲۴۶ خط)
**وظیفه:** Context-Aware Auto-completion - Section 5.3

**انواع تکمیل:**
1. **Member Access:** پیشنهاد فیلدهای struct پس از `.` یا `->`
2. **Function Args:** تکمیل آرگومان‌ها با فیلتر بر اساس expected type
3. **Scope Completions:** متغیرها، توابع، types فعال در scope جاری

**اولویت‌بندی:** local > parameter > variable > function > global

---

### بخش ۵: رابط کاربری

#### 🔹 `web/app.py` (۱۹۳ خط)
**وظیفه:** Backend API برای IDE تحت وب - Section 6.6

**Framework:** FastAPI + Jinja2

**Endpoints:**
| Endpoint | وظیفه |
|----------|-------|
| `POST /api/compile` | کامپایل و تولید تمام گزارش‌ها |
| `POST /api/hover` | Hover information |
| `POST /api/goto` | Go-to-Definition |
| `POST /api/refs` | Find References |
| `POST /api/rename` | Safe Rename |
| `POST /api/completion` | Auto-completion |

---

#### 🔹 `main.py` (۵۱۲ خط)
**وظیفه:** Orchestrator کل pipeline

**مراحل اجرا:**
1. خواندن فایل منبع
2. Lexical Analysis → tokens
3. Parsing → AST
4. ذخیره tokens و AST (JSON/TXT)
5. Syntax Highlighting → HTML
6. Symbol Table Construction (2 passes)
7. Type Checking
8. Graph Analysis (CFG + Call Graph)
9. Data Flow Analysis
10. IDE Features (Navigation, Completion, Refactoring)

---

## 📊 خروجی‌های پروژه (Deliverables)

تمام خروجی‌ها در پوشه `outputs/` تولید می‌شوند:

| فایل | توضیح | مربوط به فاز |
|------|-------|-------------|
| `tokens.json/txt` | لیست توکن‌ها با location | Phase 1 |
| `ast.json/txt` | درخت نحوی | Phase 1 |
| `highlighted_code.html` | کد رنگی شده | Phase 1 |
| `symbol_table.json/txt` | جدول نمادها کامل | Phase 2 |
| `semantic_report.json/txt` | خطاهای معنایی | Phase 2 |
| `type_errors.json/txt` | خطاهای نوع | Phase 2 |
| `cfg_report.json/txt` | CFG توابع | Phase 3 |
| `call_graph.json/txt` | Call Graph | Phase 3 |
| `data_flow_report.json/txt` | Dead code analysis | Phase 3 |
| `navigation_report.json/txt` | Navigation queries | Phase 3 |
| `completions.json/txt` | Completion suggestions | Phase 3 |
| `rename.c` | کد پس از rename | Phase 3 |
| `errors_log.json/txt` | تمام خطاها | All phases |

---

## 🚀 نحوه اجرا

### اجرای خط فرمان (CLI):
```bash
python main.py test_code.c
```

### اجرای سرور وب (Web UI):
```bash
uvicorn web.app:app --reload
```
مراجعه به `http://localhost:8000`

### Docker Deployment (Bonus):
```bash
docker-compose up --build
```

---

## ✨ نوآوری‌ها و ویژگی‌های برجسته

1. **پشتیبانی کامل از Structها** با scope اختصاصی
2. **دو پاس بودن Symbol Table Builder** برای دقت بالاتر در resolution
3. **تحلیل جریان داده واقعی** با Liveness Analysis و Definite Assignment
4. **Safe Rename** با Conflict Detection و Shadow check
5. **Auto-completion هوشمند** با درک context و type inference
6. **Navigation کامل** مشابه VSCode (Go-to-def, Find refs, Hover)
7. **خروجی‌های متنوع** JSON و TXT برای هر فاز جهت دیباگ و ارزیابی
8. **رابط وب تعاملی** با تمام قابلیت‌های IDE
9. **Error Recovery** در تمام فازها بدون crash کردن
10. **معماری ماژولار** قابل توسعه به زبان‌های دیگر

---

## 📝 نتیجه‌گیری

این پروژه یک **پیاده‌سازی کامل از Compiler Front-End همراه با Program Analysis Passes** است که دقیقاً مطابق با الزامات پروژه پایانی درس طراحی کامپایلورها توسعه یافته است.

### دستاوردهای آموزشی:
- ✅ تجربه عملی با اتوماتا، عبارات منظم، و گرامرهای صوری
- ✅ درک کامل pipeline کامپایل از کاراکتر خام تا بازنمایی معنایی
- ✅ پیاده‌سازی Scope Resolution و Type System
- ✅ ساخت زیرساخت تحلیل برنامه (CFG, Call Graph, Data-flow)
- ✅ تولید ابزار کاربردی قابل استفاده به عنوان plugin ادیتور

### ارتباط با کامپایلرهای واقعی:
الگوریتم‌ها و ساختار داده‌های پیاده‌سازی شده (DFA-driven lexing, recursive-descent parsing, symbol tables, CFGs, data-flow analysis) همان‌هایی هستند که در GCC, Clang, rustc, و Language Serverها استفاده می‌شوند.

---

**بهار ۱۴۰۴-۱۴۰۵**