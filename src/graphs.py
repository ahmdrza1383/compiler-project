from src.ast_node import (
    FunctionDef,
    CallExpr,
    ASTNode,
)


class BasicBlock:
    def __init__(self, block_id: int, label: str = ""):
        self.id = block_id
        self.label = label
        self.statements = []
        self.successors = []
        self.predecessors = []

    def add_statement(self, stmt: ASTNode):
        self.statements.append(stmt)

    def add_successor(self, block: "BasicBlock"):
        if block not in self.successors:
            self.successors.append(block)
        if self not in block.predecessors:
            block.predecessors.append(self)

    def to_dict(self):
        def get_line(node):
            if not node:
                return "?"
            if hasattr(node, "line"):
                return node.line
            if hasattr(node, "member"):
                return get_line(node.member)
            if hasattr(node, "left"):
                return get_line(node.left)
            if hasattr(node, "var_name"):
                return get_line(node.var_name)
            if hasattr(node, "func_name"):
                return get_line(node.func_name)
            if hasattr(node, "operand"):
                return get_line(node.operand)
            if hasattr(node, "obj"):
                return get_line(node.obj)
            if hasattr(node, "children") and node.children:
                return get_line(node.children[0])
            return "?"

        stmt_strings = []
        for stmt in self.statements:
            name = getattr(stmt, "name", stmt.__class__.__name__)

            line = get_line(stmt)

            if line != "?":
                stmt_strings.append(f"{name} (Line {line})")
            else:
                stmt_strings.append(name)

        return {
            "id": self.id,
            "label": self.label,
            "statements": stmt_strings,
            "successors": [b.id for b in self.successors],
        }


class CFG:
    def __init__(self, func_name: str):
        self.func_name = func_name
        self.entry_block = None
        self.exit_block = None
        self.blocks = []
        self.idoms = {}
        self.ipdoms = {}

    def to_dict(self):
        return {
            "func_name": self.func_name,
            "entry_block": self.entry_block.id if self.entry_block else None,
            "exit_block": self.exit_block.id if self.exit_block else None,
            "blocks": [b.to_dict() for b in self.blocks],
            "idoms": self.idoms,
            "ipdoms": self.ipdoms,
        }


class CFGBuilder:
    def __init__(self, ast_root):
        self.ast_root = ast_root
        self.cfgs = {}
        self.block_counter = 0
        self.current_block = None
        self.exit_block = None
        self.current_cfg = None
        self.loop_exit_stack = []
        self.loop_continue_stack = []

    def new_block(self, label: str = "") -> BasicBlock:
        b = BasicBlock(self.block_counter, label)
        self.block_counter += 1
        self.current_cfg.blocks.append(b)
        return b

    def build(self):
        for node in getattr(self.ast_root, "declarations", []):
            if type(node).__name__ == "FunctionDef":
                self._build_function_cfg(node)
        return self.cfgs

    def _build_function_cfg(self, func_node):
        func_name = func_node.func_name.id_name
        self.current_cfg = CFG(func_name)
        self.current_cfg.entry_block = self.new_block("ENTRY")
        self.exit_block = self.new_block("EXIT")
        self.current_cfg.exit_block = self.exit_block
        self.current_block = self.current_cfg.entry_block
        self._visit(func_node.body)
        if self.current_block and not self.current_block.successors:
            self.current_block.add_successor(self.exit_block)

        self._compute_dominators(self.current_cfg)
        self._compute_post_dominators(self.current_cfg)

        self.cfgs[func_name] = self.current_cfg

    def _compute_dominators(self, cfg):
        if not cfg.entry_block:
            return

        visited = set()
        po = []

        def dfs(b):
            visited.add(b.id)
            for succ in b.successors:
                if succ.id not in visited:
                    dfs(succ)
            po.append(b)

        dfs(cfg.entry_block)
        rpo = po[::-1]
        rpo_dict = {b.id: i for i, b in enumerate(rpo)}

        idoms = {b.id: None for b in cfg.blocks}
        idoms[cfg.entry_block.id] = cfg.entry_block.id

        def intersect(b1_id, b2_id):
            finger1 = b1_id
            finger2 = b2_id
            while finger1 != finger2:
                while rpo_dict.get(finger1, -1) > rpo_dict.get(finger2, -1):
                    finger1 = idoms[finger1]
                while rpo_dict.get(finger2, -1) > rpo_dict.get(finger1, -1):
                    finger2 = idoms[finger2]
            return finger1

        changed = True
        while changed:
            changed = False
            for b in rpo:
                if b.id == cfg.entry_block.id:
                    continue

                new_idom = None
                for p in b.predecessors:
                    if idoms[p.id] is not None:
                        new_idom = p.id
                        break

                if new_idom is None:
                    continue

                for p in b.predecessors:
                    if p.id != new_idom and idoms[p.id] is not None:
                        new_idom = intersect(p.id, new_idom)

                if idoms[b.id] != new_idom:
                    idoms[b.id] = new_idom
                    changed = True

        cfg.idoms = idoms

    def _compute_post_dominators(self, cfg):
        if not cfg.exit_block:
            return

        visited = set()
        po = []

        def dfs_rev(b):
            visited.add(b.id)
            for pred in b.predecessors:
                if pred.id not in visited:
                    dfs_rev(pred)
            po.append(b)

        dfs_rev(cfg.exit_block)
        rpo = po[::-1]
        rpo_dict = {b.id: i for i, b in enumerate(rpo)}

        ipdoms = {b.id: None for b in cfg.blocks}
        ipdoms[cfg.exit_block.id] = cfg.exit_block.id

        def intersect_rev(b1_id, b2_id):
            finger1 = b1_id
            finger2 = b2_id
            while finger1 != finger2:
                while rpo_dict.get(finger1, -1) > rpo_dict.get(finger2, -1):
                    finger1 = ipdoms[finger1]
                while rpo_dict.get(finger2, -1) > rpo_dict.get(finger1, -1):
                    finger2 = ipdoms[finger2]
            return finger1

        changed = True
        while changed:
            changed = False
            for b in rpo:
                if b.id == cfg.exit_block.id:
                    continue

                new_ipdom = None
                for s in b.successors:
                    if ipdoms[s.id] is not None:
                        new_ipdom = s.id
                        break

                if new_ipdom is None:
                    continue

                for s in b.successors:
                    if s.id != new_ipdom and ipdoms[s.id] is not None:
                        new_ipdom = intersect_rev(s.id, new_ipdom)

                if ipdoms[b.id] != new_ipdom:
                    ipdoms[b.id] = new_ipdom
                    changed = True

        cfg.ipdoms = ipdoms

    def _visit(self, node):
        if not node:
            return
        if self.current_block is None:
            self.current_block = self.new_block("UNREACHABLE")

        name = type(node).__name__
        if name == "Block":
            for stmt in getattr(node, "statements", []):
                self._visit(stmt)
        elif name == "IfStmt":
            self.current_block.add_statement(node.condition)
            if_head = self.current_block
            then_block = self.new_block("IF_THEN")
            merge_block = self.new_block("IF_MERGE")
            if_head.add_successor(then_block)
            self.current_block = then_block
            self._visit(node.then_branch)
            if self.current_block:
                self.current_block.add_successor(merge_block)
            if hasattr(node, "else_branch") and node.else_branch:
                else_block = self.new_block("IF_ELSE")
                if_head.add_successor(else_block)
                self.current_block = else_block
                self._visit(node.else_branch)
                if self.current_block:
                    self.current_block.add_successor(merge_block)
            else:
                if_head.add_successor(merge_block)
            self.current_block = merge_block
        elif name == "WhileStmt":
            loop_head = self.new_block("WHILE_COND")
            loop_body = self.new_block("WHILE_BODY")
            loop_exit = self.new_block("WHILE_EXIT")
            self.current_block.add_successor(loop_head)
            self.current_block = loop_head
            self.current_block.add_statement(node.condition)
            loop_head.add_successor(loop_body)
            loop_head.add_successor(loop_exit)
            self.loop_continue_stack.append(loop_head)
            self.loop_exit_stack.append(loop_exit)
            self.current_block = loop_body
            self._visit(node.body)
            if self.current_block:
                self.current_block.add_successor(loop_head)
            self.loop_continue_stack.pop()
            self.loop_exit_stack.pop()
            self.current_block = loop_exit
        elif name == "ForStmt":
            if node.init:
                if isinstance(node.init, list):
                    for stmt in node.init:
                        self.current_block.add_statement(stmt)
                else:
                    self.current_block.add_statement(node.init)
            loop_head = self.new_block("FOR_COND")
            loop_body = self.new_block("FOR_BODY")
            loop_step = self.new_block("FOR_STEP")
            loop_exit = self.new_block("FOR_EXIT")
            self.current_block.add_successor(loop_head)
            self.current_block = loop_head
            if node.condition:
                self.current_block.add_statement(node.condition)
            loop_head.add_successor(loop_body)
            loop_head.add_successor(loop_exit)
            self.loop_continue_stack.append(loop_step)
            self.loop_exit_stack.append(loop_exit)
            self.current_block = loop_body
            self._visit(node.body)
            if self.current_block:
                self.current_block.add_successor(loop_step)
            self.current_block = loop_step
            if node.step:
                self.current_block.add_statement(node.step)
            self.current_block.add_successor(loop_head)
            self.loop_continue_stack.pop()
            self.loop_exit_stack.pop()
            self.current_block = loop_exit
        elif name == "ReturnStmt":
            self.current_block.add_statement(node)
            self.current_block.add_successor(self.exit_block)
            self.current_block = None
        elif name == "BreakStmt":
            if self.loop_exit_stack:
                self.current_block.add_successor(self.loop_exit_stack[-1])
            self.current_block = None
        elif name == "ContinueStmt":
            if self.loop_continue_stack:
                self.current_block.add_successor(self.loop_continue_stack[-1])
            self.current_block = None
        else:
            if self.current_block:
                self.current_block.add_statement(node)


class CallGraphBuilder:
    def __init__(self, ast_root):
        self.ast_root = ast_root
        self.call_graph = {}

    def build(self):
        for node in getattr(self.ast_root, "declarations", []):
            if isinstance(node, FunctionDef):
                caller_name = node.func_name.id_name
                self.call_graph[caller_name] = set()
                self._find_calls(node.body, caller_name)

        return {k: list(v) for k, v in self.call_graph.items()}

    def _find_calls(self, node, caller_name):
        if not node:
            return

        if isinstance(node, CallExpr):
            if hasattr(node, "func_name") and hasattr(node.func_name, "id_name"):
                callee_name = node.func_name.id_name
                self.call_graph[caller_name].add(callee_name)

        for child in getattr(node, "children", []):
            self._find_calls(child, caller_name)
