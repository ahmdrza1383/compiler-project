import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.lexer import Lexer
from src.token import TokenType
from src.parser import Parser
from src.error_reporter import ErrorReporter, Severity
from src.highlighter import SyntaxHighlighter
from src.symbol_table_builder import SymbolTableBuilder
from src.type_checker import TypeChecker
from src.auto_completer import AutoCompleter
from src.navigation import NavigationEngine
from src.graphs import CFGBuilder, CallGraphBuilder
from src.data_flow import DataFlowAnalyzer
from src.refactoring import RenameEngine

app = FastAPI(title="Mini-C Compiler IDE")
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# ===== STATE MANAGEMENT =====
current_state = {
    "source_code": "",
    "tokens": [],
    "ast_root": None,
    "symbol_table": None,
    "nav_engine": None,
    "completer": None,
    "rename_engine": None,
    "cfgs": {},
    "call_graph": {},
    "highlighted_html": "",
}


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/compile")
async def compile_code(payload: dict):
    global current_state
    source_code = payload.get("code", "")
    current_state["source_code"] = source_code

    reporter = ErrorReporter()
    lexer = Lexer(source_code, file_name="web_code.c", reporter=reporter)
    tokens = []
    while True:
        token = lexer.next_token()
        tokens.append(token)
        if token.type == TokenType.EOF:
            break

    parser = Parser(tokens, reporter)
    ast_root = None
    try:
        ast_root = parser.parse()
    except Exception:
        pass

    syntax_errors = [d.to_dict() for d in reporter.diagnostics]
    semantic_errors = []
    semantic_warnings = []
    type_errors = []
    symbol_table = None
    cfgs = {}
    call_graph = {}
    dead_code_warnings = []
    highlighted_html = ""

    if ast_root and not reporter.has_errors():
        builder = SymbolTableBuilder(ast_root, "web_code.c", verbose=False)
        symbol_table = builder.get_symbol_table()
        semantic_errors = builder.get_errors()
        semantic_warnings = builder.warnings

        type_checker = TypeChecker(symbol_table)
        type_checker.check(ast_root)
        type_errors = type_checker.errors

        cfg_builder = CFGBuilder(ast_root)
        cfgs = cfg_builder.build()
        cg_builder = CallGraphBuilder(ast_root)
        call_graph = cg_builder.build()

        df_analyzer = DataFlowAnalyzer(cfgs, call_graph)
        dead_code_warnings = df_analyzer.analyze()

        current_state["tokens"] = tokens
        current_state["ast_root"] = ast_root
        current_state["symbol_table"] = symbol_table
        current_state["nav_engine"] = NavigationEngine(symbol_table, ast_root)
        current_state["completer"] = AutoCompleter(symbol_table, ast_root)
        current_state["rename_engine"] = RenameEngine(
            current_state["nav_engine"], source_code
        )
        current_state["cfgs"] = cfgs
        current_state["call_graph"] = call_graph

    parser_errors = [
        {"line": d.line, "col": d.col, "length": d.length}
        for d in reporter.diagnostics
        if d.severity == Severity.ERROR
    ]
    highlighter = SyntaxHighlighter(source_code, ast_root, tokens, parser_errors)
    highlighted_html = highlighter.to_html()
    current_state["highlighted_html"] = highlighted_html

    return JSONResponse(
        {
            "success": not reporter.has_errors(),
            "syntax_errors": syntax_errors,
            "semantic_errors": semantic_errors,
            "type_errors": type_errors,
            "warnings": semantic_warnings + dead_code_warnings,
            "symbol_table": symbol_table.to_dict() if symbol_table else {},
            "cfg": {func: cfg.to_dict() for func, cfg in cfgs.items()},
            "call_graph": call_graph,
            "highlighted_html": highlighted_html,
        }
    )


@app.post("/api/hover")
async def hover_info(data: dict):
    if not current_state["nav_engine"]:
        return JSONResponse(
            {"status": "error", "message": "No compiled code available"}
        )
    line = data.get("line")
    col = data.get("col")
    result = current_state["nav_engine"].get_hover_info(line, col)
    return JSONResponse(result)


@app.post("/api/goto")
async def goto_definition(data: dict):
    if not current_state["nav_engine"]:
        return JSONResponse(
            {"status": "error", "message": "No compiled code available"}
        )
    line = data.get("line")
    col = data.get("col")
    result = current_state["nav_engine"].goto_definition(line, col)
    return JSONResponse(result)


@app.post("/api/refs")
async def find_references(data: dict):
    if not current_state["nav_engine"]:
        return JSONResponse(
            {"status": "error", "message": "No compiled code available"}
        )
    line = data.get("line")
    col = data.get("col")
    result = current_state["nav_engine"].find_all_references(line, col)
    return JSONResponse(result)


@app.post("/api/rename")
async def rename_symbol(data: dict):
    if not current_state["rename_engine"]:
        return JSONResponse(
            {"status": "error", "message": "No compiled code available"}
        )
    line = data.get("line")
    col = data.get("col")
    new_name = data.get("new_name")
    if not new_name:
        return JSONResponse({"status": "error", "message": "New name is required"})
    result = current_state["rename_engine"].rename(line, col, new_name)
    if result.get("status") == "success":
        current_state["source_code"] = result["modified_source"]
    return JSONResponse(result)


@app.post("/api/completion")
async def auto_complete(data: dict):
    if not current_state["completer"]:
        return JSONResponse(
            {"status": "error", "message": "No compiled code available"}
        )
    line = data.get("line")
    col = data.get("col")
    source = current_state["source_code"]
    completions = current_state["completer"].get_completions(source, line, col)
    return JSONResponse({"status": "success", "completions": completions})
