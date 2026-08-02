from src.ast_node import (
    FunctionDef,
    Block,
    IfStmt,
    WhileStmt,
    ForStmt,
    ReturnStmt,
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
        return {
            "id": self.id,
            "label": self.label,
            "statements": [stmt.__class__.__name__ for stmt in self.statements],
            "successors": [b.id for b in self.successors],
        }


class CFG:
    def __init__(self, func_name: str):
        self.func_name = func_name
        self.entry_block = None
        self.exit_block = None
        self.blocks = []

    def to_dict(self):
        return {
            "func_name": self.func_name,
            "entry_block": self.entry_block.id if self.entry_block else None,
            "exit_block": self.exit_block.id if self.exit_block else None,
            "blocks": [b.to_dict() for b in self.blocks],
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
            if isinstance(node, FunctionDef):
                self._build_function_cfg(node)
        return self.cfgs

    def _build_function_cfg(self, func_node: FunctionDef):
        func_name = func_node.func_name.id_name
        self.current_cfg = CFG(func_name)

        self.current_cfg.entry_block = self.new_block("ENTRY")
        self.exit_block = self.new_block("EXIT")
        self.current_cfg.exit_block = self.exit_block

        self.current_block = self.current_cfg.entry_block

        self._visit(func_node.body)

        if self.current_block and not self.current_block.successors:
            self.current_block.add_successor(self.exit_block)

        self.cfgs[func_name] = self.current_cfg

    def _visit(self, node):
        if not node:
            return

        if self.current_block is None:
            self.current_block = self.new_block("UNREACHABLE")

        if isinstance(node, Block):
            for stmt in getattr(node, "statements", []):
                self._visit(stmt)

        elif isinstance(node, IfStmt):
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

        elif isinstance(node, WhileStmt):
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

        elif isinstance(node, ForStmt):
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

        elif isinstance(node, ReturnStmt):
            self.current_block.add_statement(node)
            self.current_block.add_successor(self.exit_block)
            self.current_block = None

        elif getattr(node, "name", "") == "BreakStmt":
            if self.loop_exit_stack:
                self.current_block.add_successor(self.loop_exit_stack[-1])
            self.current_block = None

        elif getattr(node, "name", "") == "ContinueStmt":
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
