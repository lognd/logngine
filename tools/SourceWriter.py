from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Iterable, Optional, Dict

class SourceElement(ABC):
    def __init__(self):
        super().__init__()
        self._indent_level = 0

    def get_indent(self) -> int:
        return self._indent_level

    def indent(self) -> None:
        self._indent_level += 1

    def deindent(self) -> None:
        self._indent_level = max(0, self._indent_level - 1)

    def inherit_indent(self, parent: SourceElement) -> None:
        self._indent_level = parent.get_indent()
        self.indent()

    def get_predeclarations(self) -> list[str]:
        return []

    def get_declarations(self) -> list[str]:
        return []

    def get_definitions(self) -> list[str]:
        return []

class SourceBuilder(ABC):
    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self) -> None:
        self._elements: list[SourceElement] = []
        self._output: list[str] = []

    def add(self, element: SourceElement) -> None:
        self._elements.append(element)

    def build(self) -> None:
        with self._section("\n#pragma region Predeclarations", "#pragma endregion  // Predeclarations"):
            for element in self._elements:
                self._add_indented(element.get_predeclarations(), element.get_indent())

        with self._section("\n#pragma region Declarations", "#pragma endregion  // Declarations"):
            for element in self._elements:
                self._add_indented(element.get_declarations(), element.get_indent())

        with self._section("\n#pragma region Definitions", "#pragma endregion  // Definitions"):
            for element in self._elements:
                self._add_indented(element.get_definitions(), element.get_indent())

    def get_output(self) -> str:
        return "\n".join(self._output)

    def __str__(self):
        return self.get_output()

    def __repr__(self):
        return self.get_output()

    def _append(self, line: str) -> None:
        self._output.append(line)

    def _prepend(self, line: str) -> None:
        self._output.insert(0, line)

    def _extend(self, lines: Iterable[str]) -> None:
        self._output.extend(lines)

    def _add_indented(self, lines: Iterable[str], level: int) -> None:
        indent = "    " * level
        self._extend(f"{indent}{line}" for line in lines)

    @contextmanager
    def _section(self, start: str, end: str, indent: int = 0):
        self._add_indented([start], indent)
        try:
            yield
        finally:
            self._add_indented([end], indent)

class SourceObject:
    class Raw(SourceElement):
        def __init__(self, content: str):
            super().__init__()
            self.content = content

        def get_definitions(self) -> list[str]:
            return [self.content]

    class Include(SourceElement):
        def __init__(self, header: str):
            super().__init__()
            self.header = header

        def get_predeclarations(self) -> list[str]:
            return [f"#include <{self.header}>"]

    class Variable(SourceElement):
        def __init__(self, type_: str, name: str, init: Optional[str | list[str]] = None):
            super().__init__()
            self.type = type_
            self.name = name
            self.initializer = init

        def set_initializer(self, init: str | list[str]) -> None:
            self.initializer = init

        def _format_initializer(self) -> str:
            if self.initializer is None:
                return "{}"
            if isinstance(self.initializer, str):
                return f"{{{self.initializer}}}"
            return f"{{{', '.join(self.initializer)}}}"

        def get_definitions(self) -> list[str]:
            if self.initializer is None:
                return [f"{self.type} {self.name}{{}};"]
            if isinstance(self.initializer, str):
                return [f"{self.type} {self.name} = {self.initializer};"]
            return [f"{self.type} {self.name} = {self._format_initializer()};"]

    class Struct(SourceElement, SourceBuilder):
        def __init__(self, name: str, **fields: str):
            SourceElement.__init__(self)
            SourceBuilder.__init__(self)
            self.name = name
            self.fields: Dict[str, SourceObject.Variable] = {
                fname: SourceObject.Variable(ftype, fname) for fname, ftype in fields.items()
            }

        def set_initializers(self, **inits):
            for name, value in inits.items():
                self.fields[name].set_initializer(value)

        def get_declarations(self) -> list[str]:
            return [f"struct {self.name};"]

        def get_definitions(self) -> list[str]:
            self._output = []
            with self._section(f"struct {self.name} {{", "};", self.get_indent()):
                self._append(f"    {self.name}() = default;")
                args = ", ".join(
                    f"{v.type + '&' if 'const' in v.type else v.type} {v.name}"
                    for v in self.fields.values()
                )
                init_list = ", ".join(f"{v.name}({v.name})" for v in self.fields.values())
                self._append(f"    {self.name}({args}): {init_list} {{}}")
                for var in self.fields.values():
                    var.inherit_indent(self)
                    self._add_indented(var.get_definitions(), var.get_indent())
            return self._output

    class Function(SourceElement, SourceBuilder):
        def __init__(self, name: str, body: list[str], return_type: str, args: list[SourceObject.Variable] = None):
            SourceElement.__init__(self)
            SourceBuilder.__init__(self)
            self.name = name
            self.body = body
            self.return_type = return_type
            self.args = args or []

        def get_definitions(self) -> list[str]:
            self._output = []
            sig = ", ".join(
                f"{a.type + '&' if 'const' in a.type else a.type} {a.name}" for a in self.args
            )
            header = f"{self.return_type} {self.name} ({sig}) {{"
            with self._section(header, "};", self.get_indent()):
                self._add_indented(self.body, self.get_indent() + 1)
            return self._output

class SourceFile(SourceBuilder):
    def __init__(self, namespace: str):
        super().__init__()
        self.namespace = namespace
        self.includes: list[SourceObject.Include] = []
        self.embedded: list[SourceObject.Raw] = []

    def add_include(self, header: str) -> None:
        self.includes.append(SourceObject.Include(header))

    def add_raw(self, raw: str) -> None:
        self.embedded.append(SourceObject.Raw(raw))

    def build(self) -> None:
        self._extend(["#pragma once"])
        for inc in self.includes:
            self._extend(inc.get_predeclarations())
        self._extend([""])
        with self._section(f"\nnamespace {self.namespace} {{", "}"):
            super().build()
            with self._section("\n#pragma region Baked-In Source File", "#pragma endregion"):
                for r in self.embedded:
                    self._extend(r.get_definitions())
