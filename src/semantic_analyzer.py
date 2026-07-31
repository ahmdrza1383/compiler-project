"""
ماژول Semantic Analyzer - طبق مستند پروژه بخش 5.1.2
Two-Pass Strategy for Forward References
"""

from src.ast_node import *
from src.symbol_table import SymbolTable, Symbol
from src.token import SourceLocation


class SemanticAnalyzer:
    """
    تحلیلگر معنایی با استراتژی دو مرحله‌ای (Two-Pass Strategy)
    طبق بخش 5.1.2 داک
    """

    def __init__(self, symbol_table: SymbolTable, source_file: str = "<stdin>"):
        self.symbol_table = symbol_table
        self.source_file = source_file
        self.errors = []

    def report_error(self, message: str, line: int, col: int):
        self.errors.append({"message": message, "line": line, "col": col})

    def analyze(self, program_node: Program) -> list:
        """
        اجرای تحلیل معنایی با استراتژی دو مرحله‌ای (Two-Pass Strategy)
        بخش 5.1.2
        """
        if not program_node:
            return self.errors

        # --- Pass 1: Declaration Scan ---
        self._pass1_declaration_scan(program_node)

        # --- Pass 2: Resolution Pass ---
        self._pass2_resolution_pass(program_node)

        return self.errors

    def _pass1_declaration_scan(self, program_node: Program):
        """مرحله اول: ثبت توابع، پروتوتایپ‌ها و استراکت‌ها در گلوبال اسکوپ"""
        for decl in program_node.declarations:
            if isinstance(decl, StructDef):
                self._scan_struct_decl(decl)
            elif isinstance(decl, FunctionDef):
                self._scan_function_decl(decl, has_body=True)
            elif isinstance(decl, FunctionDecl):
                self._scan_function_decl(decl, has_body=False)
            elif isinstance(decl, VarDecl):
                self._scan_global_var(decl)

    def _scan_struct_decl(self, node: StructDef):
        struct_name = node.struct_name.id_name
        line, col = node.struct_name.line, node.struct_name.col
        loc = SourceLocation(self.source_file, line, col)

        symbol = Symbol(
            name=struct_name,
            kind="struct",
            type_spec=f"struct {struct_name}",
            definition_loc=loc
        )
        if not self.symbol_table.define(symbol):
            self.report_error(f"Redefinition of struct '{struct_name}'", line, col)

    def _scan_function_decl(self, node, has_body=True):
        func_name = node.func_name.id_name
        line, col = node.func_name.line, node.func_name.col
        return_type_str = self._resolve_type_str(node.return_type)

        param_sigs = []
        for p in node.params:
            p_type = self._resolve_type_str(p.var_type)
            param_sigs.append(p_type)

        signature = f"({', '.join(param_sigs)}) -> {return_type_str}"
        loc = SourceLocation(self.source_file, line, col)

        symbol = Symbol(
            name=func_name,
            kind="function",
            type_spec=return_type_str,
            definition_loc=loc,
            signature=signature
        )
        if not self.symbol_table.define(symbol):
            self.report_error(f"Redefinition of function '{func_name}'", line, col)

    def _scan_global_var(self, node: VarDecl):
        var_name = node.var_name.id_name
        line, col = node.var_name.line, node.var_name.col
        var_type_str = self._resolve_type_str(node.var_type)
        loc = SourceLocation(self.source_file, line, col)

        symbol = Symbol(
            name=var_name,
            kind="variable",
            type_spec=var_type_str,
            definition_loc=loc
        )
        if not self.symbol_table.define(symbol):
            self.report_error(f"Redefinition of variable '{var_name}'", line, col)

    def _pass2_resolution_pass(self, program_node: Program):
        """مرحله دوم: پیمایش کامل درون توابع، بلوک‌ها و عبارت‌ها"""
        for decl in program_node.declarations:
            self.visit(decl)

    def visit(self, node, visited=None):
        if node is None:
            return None

        if visited is None:
            visited = set()

        if id(node) in visited:
            return None
        visited.add(id(node))

        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node, visited)

    def generic_visit(self, node, visited=None):
        if visited is None:
            visited = set()

        for key, value in node.__dict__.items():
            if key in ["parent", "name"]:
                continue
            if isinstance(value, ASTNode):
                self.visit(value, visited)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ASTNode):
                        self.visit(item, visited)

    # ===== بازدیدکننده‌ها =====

    def visit_StructDef(self, node, visited=None):
        if visited is None:
            visited = set()
        self.symbol_table.enter_scope(scope_type="struct")
        for field in node.fields:
            self.visit(field, visited)
        self.symbol_table.exit_scope()

    def visit_FunctionDef(self, node, visited=None):
        if visited is None:
            visited = set()

        self.symbol_table.enter_scope(scope_type="function")

        for param in node.params:
            self.visit_param_decl(param)

        if node.body:
            self.visit(node.body, visited)

        self.symbol_table.exit_scope()

    def visit_FunctionDecl(self, node, visited=None):
        pass

    def visit_VarDecl(self, node, visited=None):
        if visited is None:
            visited = set()

        var_name = node.var_name.id_name
        line, col = node.var_name.line, node.var_name.col
        var_type_str = self._resolve_type_str(node.var_type)

        existing = self.symbol_table.resolve(var_name)
        if existing:
            self.report_error(f"Duplicate declaration of variable '{var_name}'", line, col)
            return

        loc = SourceLocation(self.source_file, line, col)
        symbol = Symbol(
            name=var_name,
            kind="variable",
            type_spec=var_type_str,
            definition_loc=loc
        )

        if node.initializer:
            symbol.is_initialized = True
            self.visit(node.initializer, visited)

        self.symbol_table.define(symbol)

    def visit_param_decl(self, node):
        param_name = node.var_name.id_name
        line, col = node.var_name.line, node.var_name.col
        param_type_str = self._resolve_type_str(node.var_type)

        loc = SourceLocation(self.source_file, line, col)
        symbol = Symbol(
            name=param_name,
            kind="parameter",
            type_spec=param_type_str,
            definition_loc=loc,
            is_initialized=True
        )
        self.symbol_table.define(symbol)

    def visit_Block(self, node, visited=None):
        if visited is None:
            visited = set()

        self.symbol_table.enter_scope(scope_type="block")
        for stmt in node.statements:
            self.visit(stmt, visited)
        self.symbol_table.exit_scope()

    def visit_Identifier(self, node, visited=None):
        if visited is None:
            visited = set()

        name = node.id_name
        line = node.line
        col = node.col

        resolved_sym = self.symbol_table.resolve(name)
        if resolved_sym:
            resolved_sym.is_used = True
            resolved_sym.add_reference(SourceLocation(self.source_file, line, col))
        else:
            self.report_error(f"Use of undeclared identifier '{name}'", line, col)

    def visit_CallExpr(self, node, visited=None):
        if visited is None:
            visited = set()

        if hasattr(node, 'func_name') and isinstance(node.func_name, Identifier):
            func_name = node.func_name.id_name
            symbol = self.symbol_table.resolve(func_name)
            if symbol:
                symbol.is_used = True
                loc = SourceLocation(self.source_file, node.func_name.line, node.func_name.col)
                symbol.add_reference(loc)
            else:
                self.report_error(f"Undefined function: {func_name}",
                                 node.func_name.line, node.func_name.col)

        for arg in node.args if hasattr(node, 'args') else []:
            self.visit(arg, visited)

    def visit_BinaryExpr(self, node, visited=None):
        if visited is None:
            visited = set()

        if hasattr(node, 'left'):
            self.visit(node.left, visited)
        if hasattr(node, 'right'):
            self.visit(node.right, visited)

    def visit_UnaryExpr(self, node, visited=None):
        if visited is None:
            visited = set()

        if hasattr(node, 'operand'):
            self.visit(node.operand, visited)

    def visit_MemberAccess(self, node, visited=None):
        if visited is None:
            visited = set()

        if hasattr(node, 'obj'):
            self.visit(node.obj, visited)
        if hasattr(node, 'member'):
            self.visit(node.member, visited)

    def visit_IfStmt(self, node, visited=None):
        if visited is None:
            visited = set()

        if hasattr(node, 'condition'):
            self.visit(node.condition, visited)
        if hasattr(node, 'then_branch'):
            self.visit(node.then_branch, visited)
        if hasattr(node, 'else_branch'):
            self.visit(node.else_branch, visited)

    def visit_WhileStmt(self, node, visited=None):
        if visited is None:
            visited = set()

        if hasattr(node, 'condition'):
            self.visit(node.condition, visited)
        if hasattr(node, 'body'):
            self.visit(node.body, visited)

    def visit_ForStmt(self, node, visited=None):
        if visited is None:
            visited = set()

        if hasattr(node, 'init'):
            self.visit(node.init, visited)
        if hasattr(node, 'condition'):
            self.visit(node.condition, visited)
        if hasattr(node, 'step'):
            self.visit(node.step, visited)
        if hasattr(node, 'body'):
            self.visit(node.body, visited)

    def visit_ReturnStmt(self, node, visited=None):
        if visited is None:
            visited = set()

        if hasattr(node, 'value') and node.value:
            self.visit(node.value, visited)

    def _resolve_type_str(self, type_spec_node) -> str:
        if not type_spec_node:
            return "int"
        if isinstance(type_spec_node, TypeSpecifier):
            base = type_spec_node.type_name
            pointers = getattr(type_spec_node, "pointers", 0)
            return base + ("*" * pointers)
        return str(type_spec_node)