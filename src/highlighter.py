from src.ast_node import ASTNode, Identifier, Literal, SymbolCategory, TypeSpecifier, BinaryExpr, UnaryExpr

class ASTHighlighter:
    def __init__(self, source_code: str, ast_root: ASTNode):
        self.source_code = source_code
        self.ast_root = ast_root
        self.tokens_meta = []  # ذخیره قطعات کد، مختصات و دسته رنگی

    def extract_tokens(self):
        """پیمایش درخت AST برای استخراج موقعیت و دسته‌بندی رنگ‌ها"""
        self._traverse(self.ast_root)
        # مرتب‌سازی توکن‌ها بر اساس شماره خط و ستون برای پردازش ترتیبی متن
        self.tokens_meta.sort(key=lambda x: (x['line'], x['col']))
        return self.tokens_meta

    def _traverse(self, node):
        if not node:
            return

        # ۱. بررسی شناسه‌ها (Identifier) - تشخیص متغیر، تابع یا نوع
        if isinstance(node, Identifier):
            if node.category == SymbolCategory.FUNCTION:
                category = "function_ident"      # زرد / طلایی (#FFD700)
            elif node.category in (SymbolCategory.CLASS_STRUCT, SymbolCategory.TYPE):
                category = "type"                # فیروزه‌ای (#008080)
            else:
                category = "variable_ident"      # سفید / پیش‌فرض

            if hasattr(node, 'line') and hasattr(node, 'col'):
                self.tokens_meta.append({
                    "lexeme": node.id_name,
                    "line": node.line,
                    "col": node.col,
                    "length": len(node.id_name),
                    "category": category
                })

        # ۲. بررسی لیترال‌ها (Literal) - اعداد، رشته‌ها و کاراکترها
        elif isinstance(node, Literal):
            if node.type in ("INT_LIT", "FLOAT_LIT", "BIN", "HEX"):
                category = "numeric_lit"         # نارنجی (#FFA500)
            else:
                category = "string_lit"          # سبز گرم (#32CD32)

            if hasattr(node, 'line') and hasattr(node, 'col'):
                self.tokens_meta.append({
                    "lexeme": str(node.value),
                    "line": node.line,
                    "col": node.col,
                    "length": len(str(node.value)),
                    "category": category
                })

        # ۳. بررسی مشخص‌کننده‌های نوع (TypeSpecifier) مثل int, float
        elif isinstance(node, TypeSpecifier):
            if hasattr(node, 'type_name'):
                # خط و ستون را اگر در ساختارش اضافه کرده باشید اینجا می‌گیرد، در غیر این صورت از طریق فرزندان مدیریت می‌شود
                pass

        # پیمایش بازگشتی روی تمام فرزندان گره فعلی در درخت AST
        for child in node.children:
            self._traverse(child)