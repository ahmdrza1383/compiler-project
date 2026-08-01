from src.ast_node import (
    VarDecl,
    BinaryExpr,
    UnaryExpr,
    Identifier,
    ReturnStmt,
    CallExpr,
    MemberAccess,
)


class DataFlowAnalyzer:
    def __init__(self, cfgs, call_graph):
        self.cfgs = cfgs
        self.call_graph = call_graph
        self.warnings = []

    def analyze(self):
        self._find_dead_functions()
        for func_name, cfg in self.cfgs.items():
            self._find_unreachable_blocks(func_name, cfg)
            self._analyze_liveness_and_dead_stores(func_name, cfg)
        return self.warnings

    def _find_dead_functions(self):
        if "main" not in self.call_graph:
            return

        reachable = set()
        queue = ["main"]

        while queue:
            current = queue.pop(0)
            if current not in reachable:
                reachable.add(current)
                for callee in self.call_graph.get(current, []):
                    queue.append(callee)

        for func in self.call_graph.keys():
            if func not in reachable and func != "main":
                self.warnings.append(
                    f"Dead Function: '{func}' is never called from main()."
                )

    def _find_unreachable_blocks(self, func_name, cfg):
        if not cfg.entry_block:
            return

        reachable = set()
        queue = [cfg.entry_block]

        while queue:
            block = queue.pop(0)
            if block.id not in reachable:
                reachable.add(block.id)
                for succ in block.successors:
                    queue.append(succ)

        for block in cfg.blocks:
            if block.id not in reachable:
                self.warnings.append(
                    f"Unreachable Code: Block {block.id} [{block.label}] in function '{func_name}' can never be executed."
                )

    def _analyze_liveness_and_dead_stores(self, func_name, cfg):
        def_set = {}
        use_set = {}

        for block in cfg.blocks:
            d, u = self._extract_def_use(block.statements)
            def_set[block.id] = d
            use_set[block.id] = u

        in_l = {b.id: set() for b in cfg.blocks}
        out_l = {b.id: set() for b in cfg.blocks}

        changed = True
        while changed:
            changed = False
            for block in reversed(cfg.blocks):
                new_out = set()
                for succ in block.successors:
                    new_out.update(in_l[succ.id])
                out_l[block.id] = new_out

                new_in = use_set[block.id].union(out_l[block.id] - def_set[block.id])
                if new_in != in_l[block.id]:
                    in_l[block.id] = new_in
                    changed = True

        for block in cfg.blocks:
            for defined_var in def_set[block.id]:
                if (
                    defined_var not in out_l[block.id]
                    and defined_var not in use_set[block.id]
                ):
                    self.warnings.append(
                        f"Dead Store: Value assigned to '{defined_var}' in function '{func_name}' is never used subsequently."
                    )

    def _extract_def_use(self, statements):
        d_set = set()
        u_set = set()

        def visit(node, is_def=False):
            if not node:
                return
            if isinstance(node, Identifier):
                if is_def:
                    d_set.add(node.id_name)
                else:
                    u_set.add(node.id_name)
            elif isinstance(node, VarDecl):
                d_set.add(node.var_name.id_name)
                if getattr(node, "initializer", None):
                    visit(node.initializer, is_def=False)
            elif isinstance(node, BinaryExpr):
                if node.op in ["=", "+=", "-=", "*=", "/="]:
                    visit(node.left, is_def=True)
                    visit(node.right, is_def=False)
                else:
                    visit(node.left, is_def=False)
                    visit(node.right, is_def=False)
            elif isinstance(node, UnaryExpr):
                if node.op in ["++", "--"]:
                    visit(node.operand, is_def=True)
                    visit(node.operand, is_def=False)
                else:
                    visit(node.operand, is_def=False)
            elif isinstance(node, CallExpr):
                for arg in getattr(node, "args", []):
                    visit(arg, is_def=False)
            elif isinstance(node, ReturnStmt):
                if getattr(node, "value", None):
                    visit(node.value, is_def=False)
            elif isinstance(node, MemberAccess):
                visit(node.obj, is_def=False)
            else:
                for child in getattr(node, "children", []):
                    visit(child, is_def)

        for stmt in statements:
            visit(stmt)

        return d_set, u_set
