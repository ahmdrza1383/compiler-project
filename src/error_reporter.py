import json
from enum import Enum

class Severity(Enum):
    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Info"

class Diagnostic:
    def __init__(self, phase: str, severity: Severity, message: str, line: int, col: int, length: int = 1):
        self.phase = phase
        self.severity = severity
        self.message = message
        self.line = line
        self.col = col
        self.length = length

    def to_dict(self):
        return {
            "phase": self.phase,
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
            "col": self.col,
            "length": self.length
        }

    def __str__(self):
        return f"[{self.severity.value}] {self.phase} at Line {self.line}, Col {self.col}: {self.message}"


class ErrorReporter:
    def __init__(self):
        self.diagnostics = []

    def report(self, phase: str, severity: Severity, message: str, line: int, col: int, length: int = 1):
        diag = Diagnostic(phase, severity, message, line, col, length)
        self.diagnostics.append(diag)

    def has_errors(self) -> bool:
        return any(d.severity == Severity.ERROR for d in self.diagnostics)

    def export_json(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            if not self.diagnostics:
                # اگر اروری نبود، یک آبجکت جیسون با پیام موفقیت چاپ می‌شود
                json.dump({"status": "No errors found."}, f, indent=2)
            else:
                json.dump([d.to_dict() for d in self.diagnostics], f, indent=2)

    def export_txt(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            if not self.diagnostics:
                # اگر اروری نبود، در فایل متنی هم ذکر می‌شود
                f.write("No errors found.\n")
            for d in self.diagnostics:
                f.write(str(d) + "\n")