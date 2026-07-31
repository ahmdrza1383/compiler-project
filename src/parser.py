from src.token import Token, TokenType
from src.ast_node import *
from src.error_reporter import ErrorReporter, Severity

class ParseError(Exception):
    """استثنای داخلی برای مدیریت Panic-Mode"""
    pass

class Parser:
    def __init__(self, tokens: list[Token], reporter: ErrorReporter = None):
        self.tokens = tokens
        self.pos = 0
        self.reporter = reporter if reporter else ErrorReporter()

    # --- توابع کمکی پارسر ---
    
    def _loc(self, token: Token):
        """یک تابع کمکی هوشمند برای استخراج امن سطر و ستون بدون توجه به نام متغیرها در کلاس‌های دیگر"""
        loc = getattr(token, 'location', None)
        if not loc:
            return 0, 0
        line = getattr(loc, 'line', getattr(loc, 'line_num', 0))
        col = getattr(loc, 'col', getattr(loc, 'column', getattr(loc, 'col_num', 0)))
        return line, col

    def peek(self) -> Token:
        if self.is_at_end():
            return self.tokens[-1]
        return self.tokens[self.pos]

    def previous(self) -> Token:
        return self.tokens[self.pos - 1]

    def is_at_end(self) -> bool:
        return self.pos >= len(self.tokens) or self.tokens[self.pos].type == TokenType.EOF

    def advance(self) -> Token:
        if not self.is_at_end():
            self.pos += 1
        return self.previous()

    def check(self, lexeme: str = None, token_type: TokenType = None) -> bool:
        if self.is_at_end():
            return False
        if token_type and self.peek().type != token_type:
            return False
        if lexeme and self.peek().lexeme != lexeme:
            return False
        return True

    def match(self, *lexemes) -> bool:
        for lexeme in lexemes:
            if self.check(lexeme=lexeme):
                self.advance()
                return True
        return False
        
    def match_type(self, *token_types) -> bool:
        for tt in token_types:
            if self.check(token_type=tt):
                self.advance()
                return True
        return False

    def consume(self, lexeme: str, message: str) -> Token:
        if self.check(lexeme=lexeme):
            return self.advance()
            
        if self.is_at_end():
            self.error(self.peek(), f"Missing closing delimiter or unexpected EOF. {message}")
            
        self.error(self.peek(), f"Unexpected token '{self.peek().lexeme}'. {message}")

    def consume_type(self, token_type: TokenType, message: str) -> Token:
        if self.check(token_type=token_type):
            return self.advance()
            
        if self.is_at_end():
            self.error(self.peek(), f"Unexpected EOF. {message}")
            
        self.error(self.peek(), f"Unexpected token '{self.peek().lexeme}'. {message}")

    def error(self, token: Token, message: str):
        line, col = self._loc(token)
        length = len(token.lexeme) if token.lexeme else 1
        
        # ثبت ارور ساختاریافته در ریپورتر
        self.reporter.report("Parser", Severity.ERROR, message, line, col, length)
        raise ParseError()

    def synchronize(self):
        """Panic-Mode Recovery: پریدن از توکن‌ها تا رسیدن به یک نقطه امن"""
        if self.is_at_end():
            return
            
        self.advance()
        sync_tokens = ['if', 'while', 'for', 'return', 'break', 'continue', 'struct', 'int', 'float', 'double', 'char', 'void']
        while not self.is_at_end():
            if self.previous().lexeme in [';', '}']:
                return
            if self.peek().lexeme in sync_tokens:
                return
            self.advance()

    # ==========================================
    # پیاده‌سازی قوانین گرامر
    # ==========================================

    def parse(self) -> Program:
        declarations = []
        while not self.is_at_end():
            try:
                declarations.append(self.parse_declaration())
            except ParseError:
                self.synchronize()
        return Program(declarations)

    def parse_declaration(self):
        if self.check(lexeme="struct"):
            return self.parse_struct_prefix()
        return self.parse_non_struct_decl()

    def parse_struct_prefix(self):
        self.consume("struct", "Expected 'struct'")
        ident_tok = self.consume_type(TokenType.IDENTIFIER, "Expected struct name")
        line, col = self._loc(ident_tok)
        ident = Identifier(ident_tok.lexeme, SymbolCategory.CLASS_STRUCT, line, col)
        
        if self.check("{"):
            fields = self.parse_struct_body()
            return StructDef(ident, fields)
        else:
            type_spec = TypeSpecifier(f"struct {ident.id_name}")
            return self.parse_type_rest(type_spec)

    def parse_struct_body(self):
        self.consume("{", "Expected '{' for struct body")
        fields = []
        while not self.check("}") and not self.is_at_end():
            t_spec = self.parse_type_spec()
            ident_tok = self.consume_type(TokenType.IDENTIFIER, "Expected field name")
            line, col = self._loc(ident_tok)
            ident = Identifier(ident_tok.lexeme, SymbolCategory.VARIABLE, line, col)
            self.consume(";", "Expected ';' after struct field")
            fields.append(VarDecl(t_spec, ident, False, None, None))
        self.consume("}", "Expected '}'")
        self.consume(";", "Expected ';' after struct definition")
        return fields

    def parse_type_rest(self, base_type_spec):
        pointers = 0
        while self.match("*"):
            pointers += 1
            
        if pointers > 0:
            base_type_spec.pointers += pointers
            base_type_spec.name = f"Type: {base_type_spec.type_name}" + ("*" * base_type_spec.pointers)
        
        ident_tok = self.consume_type(TokenType.IDENTIFIER, "Expected identifier")
        line, col = self._loc(ident_tok)
        
        if self.match("("):
            ident = Identifier(ident_tok.lexeme, SymbolCategory.FUNCTION, line, col)
            params = []
            if not self.check(")"):
                params = self.parse_param_list()
            self.consume(")", "Expected ')' after parameters")
            if self.check("{"):
                body = self.parse_block()
                return FunctionDef(base_type_spec, ident, params, body)
            else:
                self.consume(";", "Expected ';' after function declaration")
                return FunctionDecl(base_type_spec, ident, params)
        else:
            ident = Identifier(ident_tok.lexeme, SymbolCategory.VARIABLE, line, col)
            return self.parse_var_tail(base_type_spec, ident)
        
    def parse_non_struct_decl(self):
        type_spec = self.parse_basic_type_spec()
        return self.parse_type_rest(type_spec)

    def parse_basic_type_spec(self):
        if not self.match("int", "float", "double", "char", "void"):
            self.error(self.peek(), "Expected basic type")
        type_name = self.previous().lexeme
        pointers = 0
        while self.match("*"):
            pointers += 1
        return TypeSpecifier(type_name, pointers)

    def parse_type_spec(self):
        if self.match("struct"):
            ident = self.consume_type(TokenType.IDENTIFIER, "Expected struct name")
            pointers = 0
            while self.match("*"):
                pointers += 1
            return TypeSpecifier(f"struct {ident.lexeme}", pointers)
        return self.parse_basic_type_spec()

    def parse_var_init(self, base_type_spec):
        pointers = 0
        while self.match("*"):
            pointers += 1
            
        ident_tok = self.consume_type(TokenType.IDENTIFIER, "Expected identifier in variable initialization")
        line, col = self._loc(ident_tok)
        ident = Identifier(ident_tok.lexeme, SymbolCategory.VARIABLE, line, col)
        
        is_array = False
        array_size = None
        initz = None
        
        if self.match("["):
            is_array = True
            array_size = self.parse_expr()
            self.consume("]", "Expected ']'")
            
        if self.match("="):
            initz = self.parse_initializer()
            
        var_type = TypeSpecifier(base_type_spec.type_name, base_type_spec.pointers + pointers)
        return VarDecl(var_type, ident, is_array, array_size, initz)

    def parse_var_tail(self, type_spec, first_ident):
        is_array = False
        array_size = None
        initializer = None
        
        if self.match("["):
            is_array = True
            array_size = self.parse_expr()
            self.consume("]", "Expected ']'")
            
        if self.match("="):
            initializer = self.parse_initializer() 
            
        decls = [VarDecl(type_spec, first_ident, is_array, array_size, initializer)]
        
        while self.match(","):
            decls.append(self.parse_var_init(type_spec))
            
        self.consume(";", "Expected ';' after variable declaration")
        return decls[0] if len(decls) == 1 else Block(decls)

    def parse_param_list(self):
        params = [self.parse_param()]
        while self.match(","):
            params.append(self.parse_param())
        return params

    def parse_param(self):
        t_spec = self.parse_type_spec()
        ident_tok = self.consume_type(TokenType.IDENTIFIER, "Expected parameter name")
        line, col = self._loc(ident_tok)
        ident = Identifier(ident_tok.lexeme, SymbolCategory.VARIABLE, line, col)
        is_array = False
        if self.match("["):
            is_array = True
            if not self.check("]"):
                self.parse_expr()
            self.consume("]", "Expected ']'")
        return VarDecl(t_spec, ident, is_array, None, None)

    def parse_block(self):
        self.consume("{", "Expected '{'")
        stmts = []
        while not self.check("}") and not self.is_at_end():
            try:
                stmts.append(self.parse_statement())
            except ParseError:
                self.synchronize()
        self.consume("}", "Expected '}'")
        return Block(stmts)

    def parse_statement(self):
        if self.check(lexeme="if"): return self.parse_if_stmt()
        if self.check(lexeme="while"): return self.parse_while_stmt()
        if self.check(lexeme="for"): return self.parse_for_stmt()
        if self.check(lexeme="return"): return self.parse_return_stmt()
        if self.check(lexeme="break"): return self.parse_break_stmt()
        if self.check(lexeme="continue"): return self.parse_continue_stmt()
        if self.check(lexeme="{"): return self.parse_block()
        
        if self.peek().lexeme in ["struct", "int", "float", "double", "char", "void"]:
            lookahead_pos = self.pos + 1
            while lookahead_pos < len(self.tokens) and self.tokens[lookahead_pos].lexeme == '*':
                lookahead_pos += 1
            if lookahead_pos < len(self.tokens) and self.tokens[lookahead_pos].type == TokenType.IDENTIFIER:
                return self.parse_declaration()

        return self.parse_expr_stmt()

    def parse_if_stmt(self):
        self.consume("if", "Expected 'if'")
        self.consume("(", "Expected '('")
        cond = self.parse_expr()
        self.consume(")", "Expected ')'")
        then_b = self.parse_statement()
        else_b = self.parse_statement() if self.match("else") else None
        return IfStmt(cond, then_b, else_b)

    def parse_while_stmt(self):
        self.consume("while", "Expected 'while'")
        self.consume("(", "Expected '('")
        cond = self.parse_expr()
        self.consume(")", "Expected ')'")
        body = self.parse_statement()
        return WhileStmt(cond, body)

    def parse_for_stmt(self):
        self.consume("for", "Expected 'for'")
        self.consume("(", "Expected '('")
        init = self.parse_expr() if not self.check(";") else None
        self.consume(";", "Expected ';'")
        cond = self.parse_expr() if not self.check(";") else None
        self.consume(";", "Expected ';'")
        step = self.parse_expr() if not self.check(")") else None
        self.consume(")", "Expected ')'")
        body = self.parse_statement()
        return ForStmt(init, cond, step, body)

    def parse_return_stmt(self):
        self.consume("return", "Expected 'return'")
        val = None
        if not self.check(";"):
            val = self.parse_expr()
        self.consume(";", "Expected ';'")
        return ReturnStmt(val)

    def parse_break_stmt(self):
        self.consume("break", "Expected 'break'")
        self.consume(";", "Expected ';'")
        return ASTNode(name="BreakStmt")

    def parse_continue_stmt(self):
        self.consume("continue", "Expected 'continue'")
        self.consume(";", "Expected ';'")
        return ASTNode(name="ContinueStmt")

    def parse_expr_stmt(self):
        expr = None
        if not self.check(";"):
            expr = self.parse_expr()
        self.consume(";", "Expected ';'")
        return expr

    def parse_expr(self):
        return self.parse_assignment()

    def parse_assignment(self):
        expr = self.parse_logical_or()
        if self.match("=", "+=", "-=", "*=", "/="):
            op = self.previous().lexeme
            value = self.parse_assignment()
            return BinaryExpr(op, expr, value)
        return expr

    def parse_logical_or(self):
        expr = self.parse_logical_and()
        while self.match("||"):
            op = self.previous().lexeme
            right = self.parse_logical_and()
            expr = BinaryExpr(op, expr, right)
        return expr

    def parse_logical_and(self):
        expr = self.parse_equality()
        while self.match("&&"):
            op = self.previous().lexeme
            right = self.parse_equality()
            expr = BinaryExpr(op, expr, right)
        return expr

    def parse_equality(self):
        expr = self.parse_relational()
        while self.match("==", "!="):
            op = self.previous().lexeme
            right = self.parse_relational()
            expr = BinaryExpr(op, expr, right)
        return expr

    def parse_relational(self):
        expr = self.parse_additive()
        while self.match("<", "<=", ">", ">="):
            op = self.previous().lexeme
            right = self.parse_additive()
            expr = BinaryExpr(op, expr, right)
        return expr

    def parse_additive(self):
        expr = self.parse_multiplicative()
        while self.match("+", "-"):
            op = self.previous().lexeme
            right = self.parse_multiplicative()
            expr = BinaryExpr(op, expr, right)
        return expr

    def parse_multiplicative(self):
        expr = self.parse_unary()
        while self.match("*", "/", "%"):
            op = self.previous().lexeme
            right = self.parse_unary()
            expr = BinaryExpr(op, expr, right)
        return expr

    def parse_unary(self):
        if self.match("+", "-", "*", "&", "!", "++", "--"):
            op = self.previous().lexeme
            return UnaryExpr(op, self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_primary()
        while True:
            if self.match("["):
                idx = self.parse_expr()
                self.consume("]", "Expected ']'")
                expr = ArrayAccess(expr, idx)
            elif self.match(".", "->"):
                is_ptr = self.previous().lexeme == "->"
                ident_tok = self.consume_type(TokenType.IDENTIFIER, "Expected property name")
                line, col = self._loc(ident_tok)
                ident = Identifier(ident_tok.lexeme, SymbolCategory.VARIABLE, line, col)
                expr = MemberAccess(expr, ident, is_ptr)
            elif self.match("("):
                args = []
                if not self.check(")"):
                    args = self.parse_arg_list()
                self.consume(")", "Expected ')'")
                if isinstance(expr, Identifier):
                    expr.category = SymbolCategory.FUNCTION
                    expr.name = f"ID: {expr.id_name} ({SymbolCategory.FUNCTION.value})"
                expr = CallExpr(expr, args)
            elif self.match("++", "--"):
                expr = UnaryExpr(self.previous().lexeme, expr, is_postfix=True)
            else:
                break
        return expr

    def parse_primary(self):
        if self.match_type(TokenType.INT_LIT, TokenType.FLOAT_LIT, TokenType.STRING_LIT, TokenType.CHAR_LIT):
            tok = self.previous()
            line, col = self._loc(tok)
            return Literal(tok.lexeme, tok.type.name, line, col)
        
        if self.match_type(TokenType.IDENTIFIER):
            tok = self.previous()
            line, col = self._loc(tok)
            return Identifier(tok.lexeme, SymbolCategory.VARIABLE, line, col)
            
        if self.match("("):
            expr = self.parse_expr()
            self.consume(")", "Expected ')'")
            return expr
            
        self.error(self.peek(), "Unexpected token")

    def parse_arg_list(self):
        args = [self.parse_expr()]
        while self.match(","):
            args.append(self.parse_expr())
        return args

    def parse_initializer(self):
        if self.match("{"):
            exprs = []
            if not self.check("}"):
                exprs.append(self.parse_expr())
                while self.match(","):
                    exprs.append(self.parse_expr())
            self.consume("}", "Expected '}' after initializer list")
            return ASTNode(name="InitializerList", elements=exprs)
        else:
            return self.parse_expr()