from anytree import NodeMixin
from enum import Enum

class SymbolCategory(Enum):
    VARIABLE = "Variable"
    FUNCTION = "Function"
    CLASS_STRUCT = "Struct"
    KEYWORD = "Keyword"
    TYPE = "Type"
    LITERAL = "Literal"
    OPERATOR = "Operator"

class ASTNode(NodeMixin):
    def __init__(self, **kwargs):
        # نام گره برای نمایش در anytree
        self.name = self.__class__.__name__ 
        for key, value in kwargs.items():
            setattr(self, key, value)
            # اتصال خودکار فرزندان برای ساختار درختی
            if isinstance(value, ASTNode):
                value.parent = self
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ASTNode):
                        item.parent = self

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if key == 'parent' or key.startswith('_'):
                continue
                
            # بررسی برای تبدیل امن مقادیر Enum (مثل SymbolCategory) به رشته یا مقدار پایه
            if hasattr(value, 'value'): # اگر شیء از نوع Enum باشد
                result[key] = value.value
            elif isinstance(value, list):
                result[key] = [
                    item.to_dict() if hasattr(item, 'to_dict') else (item.value if hasattr(item, 'value') else item)
                    for item in value
                ]
            elif hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            else:
                result[key] = value
                
        return result

# --- Leaf Nodes ---
class Identifier(ASTNode):
    def __init__(self, name: str, category: SymbolCategory, line: int, col: int):
        super().__init__(id_name=name, category=category, line=line, col=col)
        self.name = f"ID: {name} ({category.value})"

class Literal(ASTNode):
    def __init__(self, value, lit_type: str, line: int, col: int):
        super().__init__(value=value, type=lit_type, category=SymbolCategory.LITERAL, line=line, col=col)
        self.name = f"Literal: {value}"

class TypeSpecifier(ASTNode):
    def __init__(self, type_name: str, pointers: int = 0):
        super().__init__(type_name=type_name, pointers=pointers, category=SymbolCategory.TYPE)
        self.name = f"Type: {type_name}" + ("*" * pointers)

# --- Structure Nodes (N-ary) ---
class Program(ASTNode):
    def __init__(self, declarations: list):
        super().__init__(declarations=declarations)

class Block(ASTNode):
    def __init__(self, statements: list):
        super().__init__(statements=statements)

class FunctionDef(ASTNode):
    def __init__(self, return_type, name: Identifier, params: list, body: Block):
        super().__init__(return_type=return_type, func_name=name, params=params, body=body)

class FunctionDecl(ASTNode):
    def __init__(self, return_type, name: Identifier, params: list):
        super().__init__(return_type=return_type, func_name=name, params=params)

class StructDef(ASTNode):
    def __init__(self, name: Identifier, fields: list):
        super().__init__(struct_name=name, fields=fields)

class VarDecl(ASTNode):
    def __init__(self, var_type, name: Identifier, is_array: bool, array_size, initializer):
        super().__init__(var_type=var_type, var_name=name, is_array=is_array, array_size=array_size, initializer=initializer)

class IfStmt(ASTNode):
    def __init__(self, condition, then_branch, else_branch=None):
        super().__init__(condition=condition, then_branch=then_branch, else_branch=else_branch)

class WhileStmt(ASTNode):
    def __init__(self, condition, body):
        super().__init__(condition=condition, body=body)

class ForStmt(ASTNode):
    def __init__(self, init, condition, step, body):
        super().__init__(init=init, condition=condition, step=step, body=body)

class ReturnStmt(ASTNode):
    def __init__(self, value=None):
        super().__init__(value=value)

class CallExpr(ASTNode):
    def __init__(self, func_name, args: list):
        super().__init__(func_name=func_name, args=args)

# --- Mathematical/Logical Nodes (Binary/Unary) ---
class BinaryExpr(ASTNode):
    def __init__(self, op: str, left, right):
        super().__init__(op=op, left=left, right=right)
        self.name = f"BinaryExpr ({op})"

class UnaryExpr(ASTNode):
    def __init__(self, op: str, operand, is_postfix: bool = False):
        super().__init__(op=op, operand=operand, is_postfix=is_postfix)
        self.name = f"UnaryExpr ({op})"

class ArrayAccess(ASTNode):
    def __init__(self, array, index):
        super().__init__(array=array, index=index)

class MemberAccess(ASTNode):
    def __init__(self, obj, member: Identifier, is_pointer: bool):
        super().__init__(obj=obj, member=member, is_pointer=is_pointer)