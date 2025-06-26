from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Iterable, Optional, Type, Dict

class _SourceObject(ABC):
    def __init__(self):
        super().__init__()
        self._indent = 0

    def get_indent(self): return self._indent
    def get_predeclarations(self) -> list[str]: return []
    def get_declarations(self) -> list[str]: return []
    def get_definitions(self) -> list[str]: return []

    def indent(self): self._indent += 1
    def deindent(self): self._indent = max(0, self._indent - 1)
    def inherit_indent(self, parent: _SourceObject):
        self._indent = parent.get_indent()
        self.indent()

class _SourceWriter(ABC):
    def __init__(self):
        super().__init__()
        self.reset()
    def reset(self):
        self._content: list[_SourceObject] = []
        self._source: list[str] = []

    def add_object(self, obj: _SourceObject): self._content.append(obj)
    def build_content(self):
        with self._wrap(["", "#pragma region Predeclarations"], ["#pragma endregion  // Predeclarations"]):
            for obj in self._content: self._extend_indented(obj.get_predeclarations(), obj.get_indent())
        with self._wrap(["", "#pragma region Declarations"], ["#pragma endregion  // Declarations"]):
            for obj in self._content: self._extend_indented(obj.get_declarations(), obj.get_indent())
        with self._wrap(["", "#pragma region Definitions"], ["#pragma endregion  // Definitions"]):
            for obj in self._content: self._extend_indented(obj.get_definitions(), obj.get_indent())

    def get_content(self): return '\n'.join(self._source)
    def __str__(self): return self.get_content()
    def __repr__(self): return self.get_content()

    def _append(self, string: str): self._source.append(string)
    def _prepend(self, string: str): self._source.insert(0, string)
    def _extend(self, content: Iterable[str]): self._source.extend(content)
    def _extend_indented(self, content: Iterable[str], indent: int): self._extend(f'{"    "*indent}{ctnt}' for ctnt in content)

    @contextmanager
    def _wrap(self, prefix: list[str], suffix: list[str], pre_indent: int = 0, suf_indent: Optional[int] = None):
        if suf_indent is None: suf_indent = pre_indent
        self._extend_indented(prefix, pre_indent)
        try: yield
        finally: self._extend_indented(suffix, suf_indent)

class SourceObject:
    class Raw(_SourceObject):
        def __init__(self, string: str):
            super().__init__()
            self.string = string
        def get_definitions(self) -> list[str]: return [self.string]

    class Include(_SourceObject):
        def __init__(self, include: str):
            super().__init__()
            self.include = include
        def get_predeclarations(self) -> list[str]: return [f'#include <{self.include}>']

    class Variable(_SourceObject):
        def __init__(self, type_: str, name: str, definition: Optional[str | list[str]] = None):
            super().__init__()
            self.type = type_
            self.name = name
            self.definition = definition

        def set_definition(self, definition: str | list[str]): self.definition = definition
        def get_definition_list(self) -> str:
            if self.definition is None: return '{}'
            elif isinstance(self.definition, str): return f'{{{self.definition}}}'
            return f'{{{", ".join(self.definition)}}}'
        def get_definitions(self) -> list[str]:
            if self.definition is None: return [f'{self.type} {self.name}{{}};']
            elif isinstance(self.definition, str): return [f'{self.type} {self.name} = {self.definition};']
            def_: list[str] = [f'{self.type} {self.name} = {self.get_definition_list()};']
            return def_

    class Struct(_SourceObject, _SourceWriter):
        def __init__(self, name: str, **fields: str):
            super().__init__()
            self.name = name
            self.member_variables: Dict[str, SourceObject.Variable] = {k: SourceObject.Variable(v, k) for k, v in fields.items()}

        def set_definitions(self, **definitions):
            for name, definition in definitions.items(): self.member_variables[name].set_definition(definition)
        def get_declarations(self) -> list[str]: return [f'struct {self.name};']
        def get_definitions(self) -> list[str]:
            self._source = []
            with self._wrap([f'struct {self.name} {{'], ['};'], self.get_indent()):
                self._source += [
                    f'    {self.name}() = default;',
                    f'    {self.name}({", ".join(f"{mv_.type+"&" if "const" in mv_.type else mv_.type} {mv_.name}" for mv_ in self.member_variables.values())}): {", ".join(f"{mv_.name}({mv_.name})" for mv_ in self.member_variables.values())}{{}}'
                ]
                for mv_ in self.member_variables.values():
                    mv_.inherit_indent(self)
                    self._extend_indented(mv_.get_definitions(), mv_.get_indent())
            return self._source

    class Function(_SourceObject, _SourceWriter):
        def __init__(self, name: str, function_code: list[str], return_type: str, arguments: list[SourceObject.Variable] = None):
            super().__init__()
            if arguments is None: arguments = []
            self._name = name
            self._internal_source = function_code
            self._return_type = return_type
            self._arguments = arguments

        def get_definitions(self) -> list[str]:
            self._source = []
            with self._wrap([f'{self._return_type} {self._name} ({", ".join(f"{mv_.type+"&" if "const" in mv_.type else mv_.type} {mv_.name}" for mv_ in self._arguments)}) {{'], ['};'], self.get_indent()):
                self._extend_indented(self._internal_source, self.get_indent() + 1)
            return self._source


class SourceContainer(_SourceWriter):
    def __init__(self, namespace: str):
        super().__init__()
        self._includes: list[SourceObject.Include] = []
        self._raw_content: list[SourceObject.Raw] = []
        self._namespace = namespace

    def add_include(self, include: str):
        self._includes.append(SourceObject.Include(include))

    def add_raw(self, string: str):
        self._raw_content.append(SourceObject.Raw(string))

    def build_content(self):
        self._extend(['#pragma once'])
        for include in self._includes: self._extend(include.get_predeclarations())
        self._extend([''])
        with self._wrap([f'namespace {self._namespace} {{'], ['}']):
            super().build_content()
            with self._wrap(["", "#pragma region Baked-In Source File"], ["#pragma endregion"]):
                for raw in self._raw_content: self._extend(raw.get_definitions())
