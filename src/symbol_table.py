from src.token import SourceLocation
from typing import List, Optional, Dict, Any


class Symbol:
    """
    Fields:
        name: The identifier string
        kind: variable, function, type, parameter, class, field, method
        type: The declared or inferred type (as a type expression)
        scope: Reference to the enclosing scope node
        definition_loc: File, line, column of the declaration site
        references: List of all usage locations (file, line, column)
        signature: For functions: parameter types and return type
        is_initialized: Whether the variable has been assigned before use
        is_used: Whether the symbol is read anywhere in its scope
    """

    def __init__(
        self,
        name: str,
        kind: str,
        type_spec: str,
        definition_loc: SourceLocation,
        signature: Optional[str] = None,
        is_initialized: bool = False,
    ):
        self.name = name
        self.kind = kind
        self.type = type_spec
        self.scope = None
        self.definition_loc = definition_loc
        self.references: List[SourceLocation] = []
        self.signature = signature
        self.is_initialized = is_initialized
        self.is_used = False

    def add_reference(self, location: SourceLocation):
        self.references.append(location)

    def set_initialized(self):
        self.is_initialized = True

    def set_used(self):
        self.is_used = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "type": self.type,
            "scope": self.scope.scope_type if self.scope else None,
            "definition_loc": str(self.definition_loc),
            "references": [str(ref) for ref in self.references],
            "signature": self.signature,
            "is_initialized": self.is_initialized,
            "is_used": self.is_used,
        }

    def __repr__(self) -> str:
        return f"Symbol(name='{self.name}', kind='{self.kind}', type='{self.type}')"


class Scope:
    def __init__(self, parent: Optional["Scope"] = None, scope_type: str = "global"):
        self.parent = parent
        self.scope_type = scope_type
        self.symbols: Dict[str, Symbol] = {}
        self.children: List["Scope"] = []

    def define(self, symbol: Symbol) -> bool:
        if symbol.name in self.symbols:
            return False
        symbol.scope = self
        self.symbols[symbol.name] = symbol
        return True

    def resolve(self, name: str) -> Optional[Symbol]:

        if name in self.symbols:
            return self.symbols[name]

        if self.parent:
            return self.parent.resolve(name)

        return None

    def resolve_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def get_all_symbols(self) -> List[Symbol]:
        result = list(self.symbols.values())
        for child in self.children:
            result.extend(child.get_all_symbols())
        return result


class SymbolTable:
    def __init__(self):
        self.global_scope = Scope(scope_type="global")
        self.current_scope = self.global_scope
        self.all_symbols: List[Symbol] = []
        self.struct_scopes = {}

    def enter_scope(self, scope_type: str = "block") -> Scope:
        new_scope = Scope(self.current_scope, scope_type)
        self.current_scope.children.append(new_scope)
        self.current_scope = new_scope
        return new_scope

    def exit_scope(self) -> Scope:
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent
        return self.current_scope

    def get_current_scope(self) -> Scope:
        return self.current_scope

    def get_global_scope(self) -> Scope:
        return self.global_scope

    def define(self, symbol: Symbol) -> bool:
        if self.current_scope.define(symbol):
            self.all_symbols.append(symbol)
            return True
        return False

    def resolve(self, name: str) -> Optional[Symbol]:
        return self.current_scope.resolve(name)

    def resolve_global(self, name: str) -> Optional[Symbol]:
        return self.global_scope.resolve_local(name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "global_scope": self._scope_to_dict(self.global_scope),
            "all_symbols": [sym.to_dict() for sym in self.all_symbols],
        }

    def _scope_to_dict(self, scope: Scope) -> Dict[str, Any]:
        return {
            "type": scope.scope_type,
            "symbols": {name: sym.to_dict() for name, sym in scope.symbols.items()},
            "children": [self._scope_to_dict(child) for child in scope.children],
        }

    def print_table(self):
        print("\n" + "=" * 70)
        print("SYMBOL TABLE")
        print("=" * 70)
        self._print_scope(self.global_scope, 0)
        print("=" * 70)

    def _print_scope(self, scope: Scope, indent: int):
        prefix = "  " * indent

        if scope.scope_type == "global":
            print(f"{prefix} Global Scope")
        elif scope.scope_type == "function":
            print(f"{prefix} Function Scope")
        elif scope.scope_type == "block":
            print(f"{prefix} Block Scope")
        elif scope.scope_type == "struct":
            print(f"{prefix}  Struct Scope")
        else:
            print(f"{prefix} {scope.scope_type.capitalize()} Scope")

        for name, symbol in scope.symbols.items():
            loc = symbol.definition_loc
            refs = len(symbol.references)
            init = "✓" if symbol.is_initialized else "✗"
            used = "✓" if symbol.is_used else "✗"
            print(
                f"{prefix}  [{symbol.kind}] '{name}' : {symbol.type}  "
                f"defined at {loc.line}:{loc.column}  "
                f"(init={init}, used={used}, refs={refs})"
            )

        for child in scope.children:
            print()
            self._print_scope(child, indent + 1)
