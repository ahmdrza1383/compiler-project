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
    ArrayAccess,
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

        builtins = [
            ("printf", "(...) -> int", "int"),
            ("scanf", "(...) -> int", "int"),
            ("malloc", "(int) -> void*", "void*"),
            ("free", "(void*) -> void", "void"),
        ]

        for name, sig, ret_type in builtins:
            builtin_sym = Symbol(
                name=name,
                kind="function",
                type_spec=ret_type,
                definition_loc=SourceLocation("<builtin>", 0, 0),
                signature=sig,
            )
            builtin_sym.is_defined = True
            self.symbol_table.define(builtin_sym)

        if self.verbose:
            print("\nPASS 1: Declaration Scan")
            print("-" * 50)
        self._pass1_declaration_scan(self.ast_root)

        if self.verbose:
            print("\nPASS 2: Resolution Pass")
            print("-" * 50)
        self._pass2_resolution(self.ast_root)

    def _make_location(self, node) -> SourceLocation:
        if hasattr(node, "line") and hasattr(node, "col"):
            return SourceLocation(self.source_file, node.line, node.col)
        return SourceLocation(self.source_file, 0, 0)

    def _register_type_reference(self, type_str: str, loc: SourceLocation):
        if not type_str:
            return
        if type_str.startswith("struct "):
            base_name = type_str.split("*")[0].split("[")[0].strip()
            struct_name = base_name[7:].strip()  # حذف کلمه "struct "

            symbol = self.symbol_table.resolve(struct_name)
            if symbol and symbol.kind == "struct":
                symbol.set_used()
                symbol.add_reference(loc)

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

            existing = self.symbol_table.global_scope.resolve_local(func_name)
            if existing and existing.kind == "function":
                if existing.signature != signature:
                    self.errors.append(f"Conflicting signatures for '{func_name}'")
                elif isinstance(node, FunctionDef):
                    if getattr(existing, "is_defined", False):
                        self.errors.append(f"Redefinition of function '{func_name}'")
                    else:
                        existing.is_defined = True
            else:
                func_symbol.is_defined = isinstance(node, FunctionDef)
                if self.symbol_table.define(func_symbol):
                    if self.verbose:
                        print(f"  Registered function: {func_name} {signature}")

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
                struct_scope = Scope(
                    parent=self.symbol_table.global_scope, scope_type="struct"
                )
                struct_scope.struct_name = struct_name
                self.symbol_table.global_scope.children.append(struct_scope)
                self.symbol_table.struct_scopes[struct_name] = struct_scope
            else:
                self.errors.append(f"Redefinition of struct '{struct_name}'")
                struct_scope = Scope(
                    parent=self.symbol_table.global_scope, scope_type="struct"
                )

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
                        type_loc = (
                            self._make_location(field.var_type)
                            if hasattr(field, "var_type")
                            else loc
                        )
                        self._register_type_reference(field_type, type_loc)

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
                type_loc = (
                    self._make_location(node.var_type)
                    if hasattr(node, "var_type")
                    else loc
                )
                self._register_type_reference(var_type, type_loc)

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

        for child in getattr(node, "children", []):
            self._pass1_declaration_scan(child)

    # ==================== PASS 2 ====================
    def _pass2_resolution(self, node):
        if not node:
            return

        if isinstance(node, (FunctionDef, FunctionDecl)):
            func_name = node.func_name.id_name
            if self.verbose:
                print(f"\n  Analyzing function: {func_name}")

            func_symbol = self.symbol_table.resolve(func_name)
            if func_symbol:
                loc = self._make_location(node.func_name)
                func_symbol.add_reference(loc)
                func_symbol.set_used()

            return_type = (
                node.return_type.type_name if hasattr(node, "return_type") else "void"
            )

            loc = self._make_location(node.func_name)
            type_loc = (
                self._make_location(node.return_type)
                if hasattr(node, "return_type")
                else loc
            )
            self._register_type_reference(return_type, type_loc)

            if isinstance(node, FunctionDef):
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
                    type_loc = (
                        self._make_location(param.var_type)
                        if hasattr(param, "var_type")
                        else loc
                    )
                    self._register_type_reference(param_type, type_loc)

                    if isinstance(node, FunctionDef):
                        param_symbol = Symbol(
                            name=param_name,
                            kind="parameter",
                            type_spec=param_type,
                            definition_loc=loc,
                            is_initialized=True,
                        )
                        self.symbol_table.define(param_symbol)
                        if self.verbose:
                            print(
                                f"    Registered parameter: {param_name} : {param_type}"
                            )

            if isinstance(node, FunctionDef):
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
            # اینجا ForStmt اضافه شده تا متغیرهای حلقه را مجاز بشمارد
            if isinstance(parent, (Block, ForStmt)):
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

                outer_symbol = self.symbol_table.resolve(var_name)
                if outer_symbol:
                    self.warnings.append(
                        f"Variable '{var_name}' shadows outer declaration"
                    )
                    if self.verbose:
                        print(f"    Shadowing: {var_name} shadows outer declaration")

                loc = self._make_location(node.var_name)
                type_loc = (
                    self._make_location(node.var_type)
                    if hasattr(node, "var_type")
                    else loc
                )
                self._register_type_reference(var_type, type_loc)

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
                # TypeChecker
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

        elif isinstance(node, ArrayAccess):
            if hasattr(node, "array"):
                self._pass2_resolution(node.array)
            if hasattr(node, "index"):
                self._pass2_resolution(node.index)
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
            self.symbol_table.enter_scope("for_loop")

            if hasattr(node, "init"):
                self._pass2_resolution(node.init)
            if hasattr(node, "condition"):
                self._pass2_resolution(node.condition)
            if hasattr(node, "step"):
                self._pass2_resolution(node.step)
            if hasattr(node, "body"):
                self._pass2_resolution(node.body)

            self.symbol_table.exit_scope()
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
        if not type_spec_node:
            return "int"
        base = getattr(type_spec_node, "type_name", str(type_spec_node))
        pointers = getattr(type_spec_node, "pointers", 0)
        result = base + ("*" * pointers)
        if var_decl_node and getattr(var_decl_node, "is_array", False):
            result += "[]"
        return result

    def get_symbol_table(self):
        return self.symbol_table

    def get_errors(self):
        return self.errors

    def get_warnings(self):
        return self.warnings
