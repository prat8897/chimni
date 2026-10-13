"""Chimni - a 2D dataflow language where layout is grammar."""
from .interpreter import (  # noqa: F401
    GrammarError,
    LangError,
    Program,
    RunError,
    compile_source,
    load,
)

__version__ = "0.1.0"
__all__ = ["compile_source", "load", "Program", "LangError", "GrammarError", "RunError", "__version__"]
