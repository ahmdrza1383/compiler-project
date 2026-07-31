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
        pass

    @abstractmethod
    def is_compatible_with(self, other: "Type") -> bool:
        pass

class PrimitiveType(Type):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def is_assignable_from(self, other: Type) -> bool:
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
        self.fields = fields

    def __str__(self):
        return f"struct {self.name}"

    def is_assignable_from(self, other: Type) -> bool:
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
        if isinstance(other, ArrayType):
            if self.size is not None and other.size is not None:
                return self.size == other.size and self.base_type.is_assignable_from(other.base_type)
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
        return False

    def is_compatible_with(self, other: Type) -> bool:
        return False

class TypeChecker:
    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table
        self.errors = []
        self.warnings = []
        self.scope_stack = [set()]

    def _report_error(self, node, message):
        """Helper to extract line/col robustly and format the error"""
        line, col = "?", "?"
        if hasattr(node, 'line') and hasattr(node, 'col'):
            line, col = node.line, node.col
        elif hasattr(node, 'var_name') and hasattr(node.var_name, 'line'):
            line, col = node.var_name.line, node.var_name.col
        elif hasattr(node, 'left') and hasattr(node.left, 'line'):
            line, col = node.left.line, node.left.col
        elif hasattr(node, 'func_name') and hasattr(node.func_name, 'line'):
            line, col = node.func_name.line, node.func_name.col
            
        self.errors.append(f"{message} at Line {line}, Col {col}")

    def check(self, node):
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

    def _visit_Program(self, node):
        self.scope_stack = [set()]
        for child in node.children:
            self._visit(child)
        return None

    def _visit_Block(self, node):
        self.scope_stack.append(set())
        for child in node.children:
            self._visit(child)
        self.scope_stack.pop()
        return None

    def _visit_Literal(self, node):
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
        symbol = getattr(node, "symbol", None)
        if not symbol:
            symbol = self.symbol_table.resolve(node.id_name)
            
        if symbol:
            node.inferred_type = self._parse_type(symbol.type)
            return node.inferred_type
        else:
            self._report_error(node, f"Undefined symbol '{node.id_name}'")
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

    def _visit_BinaryExpr(self, node):
        op = node.op

        if op in ["=", "+=", "-=", "*=", "/="]:
            return self._visit_Assignment(node)

        left_type = self._visit(node.left)
        right_type = self._visit(node.right)

        if left_type is None or right_type is None:
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        if op in ["+", "-", "*", "/", "%"]:
            if isinstance(left_type, PrimitiveType) and isinstance(right_type, PrimitiveType):
                order = ["char", "int", "float", "double"]
                if left_type.name in order and right_type.name in order:
                    left_idx = order.index(left_type.name)
                    right_idx = order.index(right_type.name)
                    result_name = order[max(left_idx, right_idx)]
                    node.inferred_type = PrimitiveType(result_name)
                    return node.inferred_type
                    
            if isinstance(left_type, PointerType) and isinstance(right_type, PrimitiveType):
                node.inferred_type = left_type
                return node.inferred_type
            if isinstance(left_type, PrimitiveType) and isinstance(right_type, PointerType):
                node.inferred_type = right_type
                return node.inferred_type
                
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        if op in ["<", "<=", ">", ">=", "==", "!="]:
            if not (left_type.is_compatible_with(right_type) or right_type.is_compatible_with(left_type)):
                self._report_error(node, f"Incompatible types for comparison: {left_type} and {right_type}")
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        if op in ["&&", "||"]:
            if (isinstance(left_type, PrimitiveType) or isinstance(left_type, PointerType)) and \
               (isinstance(right_type, PrimitiveType) or isinstance(right_type, PointerType)):
                node.inferred_type = PrimitiveType("int")
                return node.inferred_type
            self._report_error(node, f"Logical operator requires scalar operands")
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
            if isinstance(operand_type, PrimitiveType) or isinstance(operand_type, PointerType):
                node.inferred_type = operand_type
            else:
                self._report_error(node, f"Invalid operand for increment/decrement")
                node.inferred_type = PrimitiveType("int")
            return node.inferred_type
            
        if node.op == "*": 
            if isinstance(operand_type, PointerType):
                node.inferred_type = operand_type.base_type
            else:
                self._report_error(node, f"Cannot dereference non-pointer type")
                node.inferred_type = PrimitiveType("int")
            return node.inferred_type
            
        if node.op == "&": 
            node.inferred_type = PointerType(operand_type)
            return node.inferred_type
            
        node.inferred_type = PrimitiveType("int")
        return node.inferred_type

    def _visit_Assignment(self, node):
        left_type = self._visit(node.left)
        right_type = self._visit(node.right)
        
        if left_type is None:
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type
            
        if right_type is None:
            node.inferred_type = left_type
            return node.inferred_type

        if not left_type.is_assignable_from(right_type):
            var_name = node.left.id_name if isinstance(node.left, Identifier) else "expression"
            self._report_error(node, f"Type mismatch in assignment to '{var_name}': cannot assign {right_type} to {left_type}")
            
        node.inferred_type = left_type
        return node.inferred_type

    def _visit_CallExpr(self, node):
        if isinstance(node.func_name, Identifier):
            func_symbol = self.symbol_table.resolve(node.func_name.id_name)
            if func_symbol and func_symbol.kind == "function":
                return_type, param_types = self._parse_function_signature(func_symbol.signature)
                
                if len(node.args) != len(param_types):
                    self._report_error(node, f"Function {node.func_name.id_name} expects {len(param_types)} arguments, got {len(node.args)}")
                    
                for i, arg in enumerate(node.args):
                    arg_type = self._visit(arg)
                    if i < len(param_types):
                        if not param_types[i].is_assignable_from(arg_type):
                            self._report_error(node, f"Argument {i + 1} type mismatch: expected {param_types[i]}, got {arg_type}")
                            
                node.inferred_type = self._parse_type(return_type)
                return node.inferred_type
            else:
                self._report_error(node, f"Function '{node.func_name.id_name}' not found")
                node.inferred_type = PrimitiveType("int")
                return node.inferred_type
                
        node.inferred_type = PrimitiveType("int")
        return node.inferred_type

    def _visit_ReturnStmt(self, node):
        if node.value:
            return_type = self._visit(node.value)
            return return_type
        return None

    def _visit_FunctionDef(self, node):
        return_type_str = node.return_type.type_name
        expected_return_type = self._parse_type(return_type_str)
        
        self.scope_stack.append(set())
        
        # پیمایش پارامترها در داخل Scope اختصاصی تابع
        if hasattr(node, 'params'):
            for param in node.params:
                self._visit(param)
        
        if node.body:
            self._visit(node.body)
        self._check_return_statements(node.body, expected_return_type)
        
        self.scope_stack.pop()

    def _visit_MemberAccess(self, node):
        obj_type = self._visit(node.obj)
        if obj_type is None:
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        struct_type = None
        if isinstance(obj_type, StructType):
            struct_type = obj_type
        elif isinstance(obj_type, PointerType) and isinstance(obj_type.base_type, StructType):
            struct_type = obj_type.base_type
        else:
            self._report_error(node, f"Member access on non-struct type: {obj_type}")
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

        field_name = node.member.id_name
        field_type = self._find_field_type(struct_type.name, field_name)

        if field_type:
            node.inferred_type = field_type
            return field_type
        else:
            self._report_error(node, f"Field '{field_name}' not found in struct '{struct_type.name}'")
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

    def _visit_ArrayAccess(self, node):
        array_type = self._visit(node.array)
        index_type = self._visit(node.index)
        
        if isinstance(array_type, ArrayType):
            node.inferred_type = array_type.base_type
            return node.inferred_type
        elif isinstance(array_type, PointerType):
            node.inferred_type = array_type.base_type
            return node.inferred_type
        else:
            self._report_error(node, f"Array access on non-array/pointer type: {array_type}")
            node.inferred_type = PrimitiveType("int")
            return node.inferred_type

    def _visit_VarDecl(self, node):
        var_name = node.var_name.id_name
        
        if var_name in self.scope_stack[-1]:
            self._report_error(node, f"Redefinition of variable '{var_name}'")
        else:
            self.scope_stack[-1].add(var_name)

        if node.initializer:
            init_type = self._visit(node.initializer)
            if init_type is None:
                return
            
            # استخراج نام پایه و تعداد پوینترها مستقیماً از درخت نحو
            base_type_name = node.var_type.type_name
            pointers_count = getattr(node.var_type, "pointers", 0)
            full_type_str = f"{base_type_name}{'*' * pointers_count}"
            
            var_type = self._parse_type(full_type_str)
            
            if not var_type.is_assignable_from(init_type):
                self._report_error(node, f"Type mismatch in variable '{var_name}' initialization: cannot assign {init_type} to {var_type}")

    def _check_return_statements(self, node, expected_type):
        if node is None:
            return
        if isinstance(node, ReturnStmt):
            if node.value:
                actual_type = self._visit(node.value)
                if not expected_type.is_assignable_from(actual_type):
                    self._report_error(node, f"Return type mismatch: expected {expected_type}, got {actual_type}")
            else:
                if not isinstance(expected_type, PrimitiveType) or expected_type.name != "void":
                    self._report_error(node, f"Return type mismatch: expected {expected_type}, got void")
            return
            
        for child in node.children:
            self._check_return_statements(child, expected_type)

    def _parse_type(self, type_str: str) -> Type:
        if type_str is None:
            return PrimitiveType("int")
        if type_str.endswith("*"):
            base = type_str[:-1].strip()
            return PointerType(self._parse_type(base))
        if "[" in type_str and "]" in type_str:
            base = type_str[: type_str.index("[")].strip()
            return ArrayType(self._parse_type(base))
        if type_str.startswith("struct "):
            struct_name = type_str[7:].strip()
            return StructType(struct_name, {})
            
        primitive_map = {
            "int": PrimitiveType("int"),
            "float": PrimitiveType("float"),
            "double": PrimitiveType("double"),
            "char": PrimitiveType("char"),
            "void": PrimitiveType("void"),
        }
        return primitive_map.get(type_str, PrimitiveType("int"))

    def _parse_function_signature(self, signature: str):
        if not signature:
            return "void", []
        if "->" in signature:
            params_part, return_part = signature.split("->")
            params_part = params_part.strip()
            return_part = return_part.strip()
        else:
            params_part = signature
            return_part = "void"
            
        if params_part.startswith("(") and params_part.endswith(")"):
            params_part = params_part[1:-1]
            
        param_types = []
        if params_part:
            for p in params_part.split(","):
                p = p.strip()
                if p:
                    param_types.append(self._parse_type(p))
        return return_part, param_types

    def _find_field_type(self, struct_name, field_name):
        struct_scope = self.symbol_table.struct_scopes.get(struct_name)
        if struct_scope:
            symbol = struct_scope.resolve_local(field_name)
            if symbol:
                return self._parse_type(symbol.type)
        return None

    def _visit_StructDef(self, node):
        # ایجاد یک Scope جدید برای فیلدهای استراکت
        self.scope_stack.append(set())
        for child in node.children:
            self._visit(child)
        self.scope_stack.pop()
        return None

    def _visit_FunctionDecl(self, node):
        # ایجاد یک Scope جدید برای پارامترهای Prototype تابع
        self.scope_stack.append(set())
        for child in node.children:
            self._visit(child)
        self.scope_stack.pop()
        return None