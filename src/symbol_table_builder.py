from src.ast_node import (
    Program,
    FunctionDef,
    FunctionDecl,
    StructDef,
    VarDecl,
    Identifier,
    Block,
    IfStmt,
    WhileStmt,
    ForStmt,
    ReturnStmt,
    BinaryExpr,
    UnaryExpr,
    CallExpr,
    MemberAccess,
)
from src.symbol_table import SymbolTable, Symbol, Scope
from src.token import SourceLocation


class SymbolTableBuilder:
    def __init__(self, ast_root, source_file="<stdin>", verbose=False):
        self.ast_root = ast_root
        self.source_file = source_file
        self.symbol_table = SymbolTable()
        self.errors = []
        self.warnings = []
        self.verbose = verbose

        if not ast_root:
            return

        if self.verbose:
            print("\nPASS 1: Declaration Scan")
            print("-" * 50)

        self._pass1_declaration_scan(self.ast_root)

        if self.verbose:
            print("\nPASS 2: Resolution Pass")
            print("-" * 50)

        self._pass2_resolution(self.ast_root)

        # بررسی متغیرهای استفاده‌نشده (فقط یک بار در پایان کار)
        self._check_unused_variables()

    def _make_location(self, node) -> SourceLocation:
        if hasattr(node, "line") and hasattr(node, "col"):
            return SourceLocation(self.source_file, node.line, node.col)
        return SourceLocation(self.source_file, 0, 0)

    # ==================== PASS 1 ====================

    def _pass1_declaration_scan(self, node):
        if not node:
            return

        if isinstance(node, (FunctionDef, FunctionDecl)):
            func_name = node.func_name.id_name
            params = []
            for param in node.params:
                if hasattr(param, "var_type"):
                    params.append(self._resolve_type_str(param.var_type, param))
            return_type = (
                node.return_type.type_name if hasattr(node, "return_type") else "void"
            )
            signature = f"({', '.join(params)}) -> {return_type}"

            loc = self._make_location(node.func_name)
            func_symbol = Symbol(
                name=func_name,
                kind="function",
                type_spec=return_type,
                definition_loc=loc,
                signature=signature,
            )
            if self.symbol_table.define(func_symbol):
                if self.verbose:
                    print(f"  Registered function: {func_name} {signature}")
            else:
                self.errors.append(f"Redefinition of function '{func_name}'")

        elif isinstance(node, StructDef):
            struct_name = node.struct_name.id_name
            loc = self._make_location(node.struct_name)

            struct_symbol = Symbol(
                name=struct_name,
                kind="struct",
                type_spec=f"struct {struct_name}",
                definition_loc=loc,
            )
            if self.symbol_table.define(struct_symbol):
                if self.verbose:
                    print(f"  Registered struct: {struct_name}")
            else:
                self.errors.append(f"Redefinition of struct '{struct_name}'")

            struct_scope = Scope(
                parent=self.symbol_table.global_scope, scope_type="struct"
            )
            struct_scope.struct_name = struct_name
            self.symbol_table.global_scope.children.append(struct_scope)
            self.symbol_table.struct_scopes[struct_name] = struct_scope

            if hasattr(node, "fields"):
                for field in node.fields:
                    if isinstance(field, VarDecl):
                        field_name = field.var_name.id_name
                        field_type = (
                            self._resolve_type_str(field.var_type, field)
                            if hasattr(field, "var_type")
                            else "unknown"
                        )
                        loc = self._make_location(field.var_name)
                        field_symbol = Symbol(
                            name=field_name,
                            kind="field",
                            type_spec=field_type,
                            definition_loc=loc,
                        )
                        struct_scope.define(field_symbol)
                        if self.verbose:
                            print(f"    Registered field: {field_name} : {field_type}")

        elif isinstance(node, VarDecl):
            parent = getattr(node, "parent", None)
            if isinstance(parent, Program):
                var_name = node.var_name.id_name
                var_type = (
                    self._resolve_type_str(node.var_type, node)
                    if hasattr(node, "var_type")
                    else "unknown"
                )
                loc = self._make_location(node.var_name)
                var_symbol = Symbol(
                    name=var_name,
                    kind="variable",
                    type_spec=var_type,
                    definition_loc=loc,
                )
                if self.symbol_table.define(var_symbol):
                    if self.verbose:
                        print(f"  Registered global variable: {var_name} : {var_type}")
                else:
                    self.errors.append(f"Redefinition of global variable '{var_name}'")

        # استفاده از getattr برای جلوگیری از خطا در صورت عدم وجود children در برخی نودها
        for child in getattr(node, "children", []):
            self._pass1_declaration_scan(child)

    # ==================== PASS 2 ====================

    def _pass2_resolution(self, node):
        if not node:
            return

        if isinstance(node, FunctionDef):
            func_name = node.func_name.id_name
            if self.verbose:
                print(f"\n  Analyzing function: {func_name}")

            self.symbol_table.enter_scope("function")

            for param in node.params:
                if hasattr(param, "var_name"):
                    param_name = param.var_name.id_name
                    param_type = (
                        self._resolve_type_str(param.var_type, param)
                        if hasattr(param, "var_type")
                        else "unknown"
                    )
                    loc = self._make_location(param.var_name)
                    param_symbol = Symbol(
                        name=param_name,
                        kind="parameter",
                        type_spec=param_type,
                        definition_loc=loc,
                        is_initialized=True,
                    )
                    self.symbol_table.define(param_symbol)
                    if self.verbose:
                        print(f"    Registered parameter: {param_name} : {param_type}")

            if hasattr(node, "body"):
                self._pass2_resolution(node.body)

            self.symbol_table.exit_scope()
            if self.verbose:
                print(f"  Finished analyzing: {func_name}")
            return

        elif isinstance(node, Block):
            self.symbol_table.enter_scope("block")
            for stmt in node.statements if hasattr(node, "statements") else []:
                self._pass2_resolution(stmt)
            self.symbol_table.exit_scope()
            return

        elif isinstance(node, VarDecl):
            parent = getattr(node, "parent", None)
            if isinstance(parent, Block):
                var_name = node.var_name.id_name
                var_type = (
                    self._resolve_type_str(node.var_type, node)
                    if hasattr(node, "var_type")
                    else "unknown"
                )

                existing = self.symbol_table.get_current_scope().resolve_local(var_name)
                if existing:
                    line = node.var_name.line if hasattr(node.var_name, "line") else 0
                    col = node.var_name.col if hasattr(node.var_name, "col") else 0
                    self.errors.append(
                        f"Duplicate declaration: {var_name} at {line}:{col}"
                    )
                    if self.verbose:
                        print(f"    Duplicate (same scope): {var_name}")
                    return

                loc = self._make_location(node.var_name)
                var_symbol = Symbol(
                    name=var_name,
                    kind="variable",
                    type_spec=var_type,
                    definition_loc=loc,
                )
                self.symbol_table.define(var_symbol)
                if self.verbose:
                    print(f"    Registered local variable: {var_name} : {var_type}")

                if hasattr(node, "initializer") and node.initializer:
                    var_symbol.set_initialized()
                    self._pass2_resolution(node.initializer)

                outer_symbol = self.symbol_table.resolve(var_name)
                if (
                    outer_symbol
                    and outer_symbol.scope != self.symbol_table.get_current_scope()
                ):
                    self.warnings.append(
                        f"Variable '{var_name}' shadows outer declaration"
                    )
                    if self.verbose:
                        print(f"    Shadowing: {var_name} shadows outer declaration")
                return
            else:
                if hasattr(node, "initializer") and node.initializer:
                    self._pass2_resolution(node.initializer)
                return

        elif isinstance(node, Identifier):
            symbol = self.symbol_table.resolve(node.id_name)
            if symbol:
                symbol.set_used()
                loc = self._make_location(node)
                symbol.add_reference(loc)
                # پیوند نماد به گره برای استفاده در TypeChecker
                node.symbol = symbol
            else:
                line = node.line if hasattr(node, "line") else 0
                col = node.col if hasattr(node, "col") else 0
                self.errors.append(f"Undefined symbol: {node.id_name} at {line}:{col}")
            return

        elif isinstance(node, CallExpr):
            if hasattr(node, "func_name") and isinstance(node.func_name, Identifier):
                func_name = node.func_name.id_name
                symbol = self.symbol_table.resolve(func_name)
                if symbol:
                    symbol.set_used()
                    loc = self._make_location(node.func_name)
                    symbol.add_reference(loc)
                    # پیوند نماد تابع برای استفاده در TypeChecker
                    node.func_name.symbol = symbol
                    if self.verbose:
                        print(f"    Call to function: {func_name}")
                else:
                    line = node.func_name.line if hasattr(node.func_name, "line") else 0
                    col = node.func_name.col if hasattr(node.func_name, "col") else 0
                    self.errors.append(
                        f"Undefined function: {func_name} at {line}:{col}"
                    )
                    if self.verbose:
                        print(f"    Undefined function: {func_name}")

            for arg in node.args if hasattr(node, "args") else []:
                self._pass2_resolution(arg)
            return

        elif isinstance(node, (BinaryExpr, UnaryExpr)):
            if hasattr(node, "left"):
                self._pass2_resolution(node.left)
            if hasattr(node, "right"):
                self._pass2_resolution(node.right)
            if hasattr(node, "operand"):
                self._pass2_resolution(node.operand)
            return

        elif isinstance(node, MemberAccess):
            if hasattr(node, "obj"):
                self._pass2_resolution(node.obj)
            return

        elif isinstance(node, IfStmt):
            if hasattr(node, "condition"):
                self._pass2_resolution(node.condition)
            if hasattr(node, "then_branch"):
                self._pass2_resolution(node.then_branch)
            if hasattr(node, "else_branch"):
                self._pass2_resolution(node.else_branch)
            return

        elif isinstance(node, WhileStmt):
            if hasattr(node, "condition"):
                self._pass2_resolution(node.condition)
            if hasattr(node, "body"):
                self._pass2_resolution(node.body)
            return

        elif isinstance(node, ForStmt):
            if hasattr(node, "init"):
                self._pass2_resolution(node.init)
            if hasattr(node, "condition"):
                self._pass2_resolution(node.condition)
            if hasattr(node, "step"):
                self._pass2_resolution(node.step)
            if hasattr(node, "body"):
                self._pass2_resolution(node.body)
            return

        elif isinstance(node, ReturnStmt):
            if hasattr(node, "value") and node.value:
                self._pass2_resolution(node.value)
            return

        for child in getattr(node, "children", []):
            self._pass2_resolution(child)

    def _check_unused_variables(self):
        for symbol in self.symbol_table.all_symbols:
            if symbol.kind in ["variable", "parameter"] and not symbol.is_used:
                self.warnings.append(f"Unused variable: {symbol.name}")

    def _resolve_type_str(self, type_spec_node, var_decl_node=None) -> str:
        """
        تبدیل گره TypeSpecifier به رشته (مانند int* یا float[])
        طراحی‌شده بر اساس ساختار کلاس VarDecl
        """
        if not type_spec_node:
            return "int"

        base = getattr(type_spec_node, "type_name", str(type_spec_node))
        pointers = getattr(type_spec_node, "pointers", 0)
        result = base + ("*" * pointers)

        # اگر متغیر آرایه باشد (بررسی از طریق ویژگی is_array در VarDecl)
        if var_decl_node and getattr(var_decl_node, "is_array", False):
            result += "[]"

        return result

    def get_symbol_table(self):
        return self.symbol_table

    def get_errors(self):
        return self.errors

    def get_warnings(self):
        return self.warnings
