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

app = FastAPI(title="Mini-C Compiler IDE")

# اتصال پوشه‌های استاتیک و تمپلیت
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/compile")
async def compile_code(payload: dict):
    source_code = payload.get("code", "")

    # 1. Lexer & Parser
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
    except Exception as e:
        pass

    # جمع‌آوری خطاها
    syntax_errors = [d.to_dict() for d in reporter.diagnostics]

    semantic_errors = []
    semantic_warnings = []
    type_errors = []
    symbol_table_data = {}
    cfg_data = {}
    call_graph_data = {}
    dead_code_warnings = []

    if ast_root and not reporter.has_errors():
        # Symbol Table & Semantic Analysis
        builder = SymbolTableBuilder(ast_root, "web_code.c", verbose=False)
        symbol_table = builder.get_symbol_table()
        semantic_errors = builder.get_errors()
        semantic_warnings = builder.warnings
        symbol_table_data = symbol_table.to_dict()

        # Type Checker
        type_checker = TypeChecker(symbol_table)
        type_checker.check(ast_root)
        type_errors = type_checker.errors

        # Graphs (CFG & Call Graph)
        cfg_builder = CFGBuilder(ast_root)
        cfgs = cfg_builder.build()
        cfg_data = {func: cfg.to_dict() for func, cfg in cfgs.items()}

        cg_builder = CallGraphBuilder(ast_root)
        call_graph_data = cg_builder.build()

        # Data Flow Analysis
        df_analyzer = DataFlowAnalyzer(cfgs, call_graph_data)
        dead_code_warnings = df_analyzer.analyze()

    # Syntax Highlighter HTML
    parser_errors = [
        {"line": d.line, "col": d.col, "length": d.length}
        for d in reporter.diagnostics
        if d.severity == Severity.ERROR
    ]
    highlighter = SyntaxHighlighter(source_code, ast_root, tokens, parser_errors)
    highlighted_html = highlighter.to_html()

    return JSONResponse(
        {
            "success": not reporter.has_errors(),
            "syntax_errors": syntax_errors,
            "semantic_errors": semantic_errors,
            "type_errors": type_errors,
            "warnings": semantic_warnings + dead_code_warnings,
            "symbol_table": symbol_table_data,
            "cfg": cfg_data,
            "call_graph": call_graph_data,
            "highlighted_html": highlighted_html,
        }
    )
