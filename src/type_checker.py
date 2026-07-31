from abc import ABC, abstractmethod
from .ast_node import *
from .symbol_table import SymbolTable, Symbol
from .token import SourceLocation


class Type(ABC):
    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def is_assignable_from(self, other: "Type") -> bool:
        """Check if a value of 'other' type can be assigned to this type"""
        pass

    @abstractmethod
    def is_compatible_with(self, other: "Type") -> bool:
        """Check if two types are compatible (for binary operations)"""
        pass


class PrimitiveType(Type):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def is_assignable_from(self, other: Type) -> bool:
        # Implicit widening rules: char -> int -> float -> double
        if isinstance(other, PrimitiveType):
            order = ["char", "int", "float", "double"]
            if self.name in order and other.name in order:
                return order.index(other.name) <= order.index(self.name)
        return False

    def is_compatible_with(self, other: Type) -> bool:
        if isinstance(other, PrimitiveType):
            return self.name == other.name
        return False


class PointerType(Type):
    def __init__(self, base_type: Type):
        self.base_type = base_type

    def __str__(self):
        return f"{self.base_type}*"

    def is_assignable_from(self, other: Type) -> bool:
        if isinstance(other, PointerType):
            return self.base_type.is_assignable_from(other.base_type)
        # void* can accept any pointer
        if isinstance(self.base_type, PrimitiveType) and self.base_type.name == "void":
            return isinstance(other, PointerType)
        return False

    def is_compatible_with(self, other: Type) -> bool:
        if isinstance(other, PointerType):
            return self.base_type.is_compatible_with(other.base_type)
        return False


class StructType(Type):
    def __init__(self, name: str, fields: dict):
        self.name = name
        self.fields = fields  # field_name -> Type

    def __str__(self):
        return f"struct {self.name}"

    def is_assignable_from(self, other: Type) -> bool:
        # Structs are assignable only if exactly the same type
        return isinstance(other, StructType) and self.name == other.name

    def is_compatible_with(self, other: Type) -> bool:
        return self.is_assignable_from(other)


class ArrayType(Type):
    def __init__(self, base_type: Type, size: int = None):
        self.base_type = base_type
        self.size = size

    def __str__(self):
        if self.size is not None:
            return f"{self.base_type}[{self.size}]"
        return f"{self.base_type}[]"

    def is_assignable_from(self, other: Type) -> bool:
        # Array to pointer decay is handled separately
        if isinstance(other, ArrayType):
            if self.size is not None and other.size is not None:
                return self.size == other.size and self.base_type.is_assignable_from(
                    other.base_type
                )
            return self.base_type.is_assignable_from(other.base_type)
        return False

    def is_compatible_with(self, other: Type) -> bool:
        return self.is_assignable_from(other)


class FunctionType(Type):
    def __init__(self, param_types: list, return_type: Type):
        self.param_types = param_types
        self.return_type = return_type

    def __str__(self):
        params = ", ".join(str(t) for t in self.param_types)
        return f"({params}) -> {self.return_type}"

    def is_assignable_from(self, other: Type) -> bool:
        return False  # Functions are not assignable

    def is_compatible_with(self, other: Type) -> bool:
        return False


# src/type_checker.py (ادامه)


class TypeChecker:
    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self.errors = []
        self.warnings = []

    def check(self, node):
        """Main entry point for type checking"""
        if node is None:
            return None
        return self._visit(node)

    def _visit(self, node):
        method = getattr(self, f"_visit_{node.__class__.__name__}", self._visit_default)
        return method(node)

    def _visit_default(self, node):
        for child in node.children:
            self._visit(child)
        return None

    def _visit_Literal(self, node):
        """Determine type of literal"""
        if node.type == "INT_LIT":
            node.inferred_type = PrimitiveType("int")
        elif node.type == "FLOAT_LIT":
            node.inferred_type = PrimitiveType("float")
        elif node.type == "STRING_LIT":
            node.inferred_type = PointerType(PrimitiveType("char"))
        elif node.type == "CHAR_LIT":
            node.inferred_type = PrimitiveType("char")
        else:
            node.inferred_type = PrimitiveType("int")
        return node.inferred_type

    def _visit_Identifier(self, node):
        """Resolve identifier type from symbol table"""
        symbol = self.symbol_table.resolve(node.id_name)
        if symbol:
            # Convert string type to Type object
            node.inferred_type = self._parse_type(symbol.type)
            return node.inferred_type
        else:
            # Will be caught by semantic analysis
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

    def _visit_BinaryExpr(self, node):
        left_type = self._visit(node.left)
        right_type = self._visit(node.right)

        if left_type is None or right_type is None:
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        op = node.op

        # Arithmetic operators: +, -, *, /, %
        if op in ["+", "-", "*", "/", "%"]:
            # If either is float/double, result is float/double
            if isinstance(left_type, PrimitiveType) and isinstance(
                right_type, PrimitiveType
            ):
                order = ["char", "int", "float", "double"]
                if left_type.name in order and right_type.name in order:
                    left_idx = order.index(left_type.name)
                    right_idx = order.index(right_type.name)
                    result_name = order[max(left_idx, right_idx)]
                    node.inferred_type = PrimitiveType(result_name)
                    return node.inferred_type

            # Pointer arithmetic: ptr + int or int + ptr
            if isinstance(left_type, PointerType) and isinstance(
                right_type, PrimitiveType
            ):
                node.inferred_type = left_type
                return node.inferred_type
            if isinstance(left_type, PrimitiveType) and isinstance(
                right_type, PointerType
            ):
                node.inferred_type = right_type
                return node.inferred_type

            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        # Comparison operators: <, <=, >, >=, ==, !=
        if op in ["<", "<=", ">", ">=", "==", "!="]:
            # Both operands must be comparable
            if left_type.is_compatible_with(
                right_type
            ) or right_type.is_compatible_with(left_type):
                node.inferred_type = PrimitiveType("int")
            else:
                self.errors.append(
                    f"Incompatible types for comparison: {left_type} and {right_type}"
                )
                node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        # Logical operators: &&, ||
        if op in ["&&", "||"]:
            # Both operands must be scalar (int, pointer, etc.)
            if isinstance(left_type, PrimitiveType) or isinstance(
                left_type, PointerType
            ):
                if isinstance(right_type, PrimitiveType) or isinstance(
                    right_type, PointerType
                ):
                    node.inferred_type = PrimitiveType("int")
                    return node.inferred_type
            self.errors.append(f"Logical operator requires scalar operands")
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        node.inferred_type = PrimitiveType("int")
        return node.inferred_type

    def _visit_UnaryExpr(self, node):
        operand_type = self._visit(node.operand)

        if node.op in ["+", "-"]:
            if isinstance(operand_type, PrimitiveType):
                node.inferred_type = operand_type
            else:
                node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        if node.op == "!":
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        if node.op in ["++", "--"]:
            if isinstance(operand_type, PrimitiveType) or isinstance(
                operand_type, PointerType
            ):
                node.inferred_type = operand_type
            else:
                self.errors.append(f"Invalid operand for increment/decrement")
                node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        if node.op == "*":  # Dereference
            if isinstance(operand_type, PointerType):
                node.inferred_type = operand_type.base_type
            else:
                self.errors.append(f"Cannot dereference non-pointer type")
                node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        if node.op == "&":  # Address-of
            node.inferred_type = PointerType(operand_type)
            return node.inferred_type

        node.inferred_type = PrimitiveType("int")
        return node.inferred_type

    def _visit_Assignment(self, node):
        """Handle assignment in BinaryExpr with op '='"""
        left_type = self._visit(node.left)
        right_type = self._visit(node.right)

        if left_type is None:
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        if not left_type.is_assignable_from(right_type):
            self.errors.append(
                f"Type mismatch in assignment: cannot assign {right_type} to {left_type}"
            )
            # Try implicit conversion
            if isinstance(left_type, PrimitiveType) and isinstance(
                right_type, PrimitiveType
            ):
                # Implicit widening allowed
                order = ["char", "int", "float", "double"]
                if left_type.name in order and right_type.name in order:
                    if order.index(right_type.name) <= order.index(left_type.name):
                        node.inferred_type = left_type
                        return node.inferred_type
            # Pointer to void* allowed
            if (
                isinstance(left_type, PointerType)
                and isinstance(left_type.base_type, PrimitiveType)
                and left_type.base_type.name == "void"
            ):
                if isinstance(right_type, PointerType):
                    node.inferred_type = left_type
                    return node.inferred_type

        node.inferred_type = left_type
        return node.inferred_type

    def _visit_CallExpr(self, node):
        """Type check function call"""
        # Resolve function symbol
        if isinstance(node.func_name, Identifier):
            func_symbol = self.symbol_table.resolve(node.func_name.id_name)
            if func_symbol and func_symbol.kind == "function":
                # Parse function signature
                return_type, param_types = self._parse_function_signature(
                    func_symbol.signature
                )

                # Check argument count
                if len(node.args) != len(param_types):
                    self.errors.append(
                        f"Function {node.func_name.id_name} expects {len(param_types)} arguments, got {len(node.args)}"
                    )

                # Check argument types
                for i, arg in enumerate(node.args):
                    arg_type = self._visit(arg)
                    if i < len(param_types):
                        if not param_types[i].is_assignable_from(arg_type):
                            self.errors.append(
                                f"Argument {i + 1} type mismatch: expected {param_types[i]}, got {arg_type}"
                            )

                node.inferred_type = self._parse_type(return_type)
                return node.inferred_type
            else:
                self.errors.append(f"Function '{node.func_name.id_name}' not found")
                node.inferred_type = PrimitiveType("int")
                return node.inferred_type

        node.inferred_type = PrimitiveType("int")
        return node.inferred_type

    def _visit_ReturnStmt(self, node):
        """Type check return statement"""
        if node.value:
            return_type = self._visit(node.value)
            # The actual return type should be compared with function return type
            # This will be done at function level
            return return_type
        return None

    def _visit_FunctionDef(self, node):
        """Type check function body"""
        # Enter function scope
        self.symbol_table.enter_scope("function")

        # Check return statement types
        return_type_str = node.return_type.type_name
        expected_return_type = self._parse_type(return_type_str)

        if node.body:
            self._visit(node.body)

        # Check all return statements in function
        # This requires traversing the AST to find ReturnStmt nodes
        self._check_return_statements(node.body, expected_return_type)

        self.symbol_table.exit_scope()

    def _check_return_statements(self, node, expected_type):
        """Recursively find ReturnStmt and check their types"""
        if node is None:
            return

        if isinstance(node, ReturnStmt):
            if node.value:
                actual_type = self._visit(node.value)
                if not expected_type.is_assignable_from(actual_type):
                    self.errors.append(
                        f"Return type mismatch: expected {expected_type}, got {actual_type}"
                    )
            else:
                # void return
                if (
                    not isinstance(expected_type, PrimitiveType)
                    or expected_type.name != "void"
                ):
                    self.errors.append(
                        f"Return type mismatch: expected {expected_type}, got void"
                    )
            return

        for child in node.children:
            self._check_return_statements(child, expected_type)

    def _parse_type(self, type_str: str) -> Type:
        """Parse string type representation to Type object"""
        if type_str is None:
            return PrimitiveType("int")

        # Handle pointer types
        if type_str.endswith("*"):
            base = type_str[:-1].strip()
            return PointerType(self._parse_type(base))

        # Handle array types (simplified)
        if "[" in type_str and "]" in type_str:
            base = type_str[: type_str.index("[")].strip()
            return ArrayType(self._parse_type(base))

        # Handle struct types
        if type_str.startswith("struct "):
            struct_name = type_str[7:].strip()
            return StructType(struct_name, {})

        # Primitive types
        primitive_map = {
            "int": PrimitiveType("int"),
            "float": PrimitiveType("float"),
            "double": PrimitiveType("double"),
            "char": PrimitiveType("char"),
            "void": PrimitiveType("void"),
        }
        return primitive_map.get(type_str, PrimitiveType("int"))

    def _parse_function_signature(self, signature: str):
        """Parse function signature like '(int, char*) -> int'"""
        if not signature:
            return "void", []

        # Split into parameters and return type
        if "->" in signature:
            params_part, return_part = signature.split("->")
            params_part = params_part.strip()
            return_part = return_part.strip()
        else:
            params_part = signature
            return_part = "void"

        # Parse parameters
        if params_part.startswith("(") and params_part.endswith(")"):
            params_part = params_part[1:-1]
        param_types = []
        if params_part:
            for p in params_part.split(","):
                p = p.strip()
                if p:
                    param_types.append(self._parse_type(p))

        return return_part, param_types
