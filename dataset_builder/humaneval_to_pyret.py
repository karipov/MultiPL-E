from abc import ABC, abstractmethod
from typing import Tuple, List, TypeVar, Generic
import ast
import re

# We turn multi-line docstrings into single-line comments. This captures the
# start of the line.
DOCSTRING_LINESTART_RE = re.compile("""\n(\\s*)""")

# global variable that checks if we need to define our own hashmap data type
# Note: in Pyret there are only dictionaries with string keys
# otherwise, it is common to write your own key-value datatype
needs_hashmap = False
hashmap_definition = "data Pair<T, V>: | pair(key :: T, value :: V) end\n" \
                    + "type HashMap<T, V> = List<Pair<T, V>>\n\n"
TargetExp = TypeVar('TargetExp') 


def translate_type(some_type: "ast") -> str:
    global needs_hashmap
    match some_type:
        case ast.Subscript(ast.Name("List"), elts, _):
            return f"List<{translate_type(elts)}>"
        case ast.Subscript(ast.Name("Tuple"), ast.Tuple(elts, _), _):
            return "{" + "; ".join([translate_type(elt) for elt in elts]) + "}"
        case ast.Subscript(ast.Name("Dict"), ast.Tuple([ast.Name(k), ast.Name(v)], _), _):
            needs_hashmap = True
            key, value = translate_type(k), translate_type(v)
            return f"HashMap<{key}, {value}>"
        case ast.Subscript(ast.Name("Optional"), elts, _):
            return f"Option<{translate_type(elts)}>"
        case ast.Name("int") | ast.Name("float") | "int" | "float":
            return "Number"
        case ast.Name("bool") | "bool":
            return "Boolean"
        case ast.Name("str") | "str":
            return "String"
        case _:
            return "Any" # FIXME: bad practice? should probably not have a type at all?

def coerce(expr: str, some_type) -> str:
    def coerce_to_option(expr: str) -> str:
        return expr if expr == "none" else f"some({expr})"

    match expr, some_type:
        case _, ast.Subscript(ast.Name("Optional"), _):
            return coerce_to_option(expr)
        case _:
            return expr



class Translator:

    stop = ["\nend"]

    def gen_literal(self, c: bool | str | int | float | None) -> TargetExp:
        if type(c) == bool:
            return repr(c).lower()
        elif type(c) == str:
            return f'"{c}"'
        else:
            return repr(c)

    def gen_var(self, v: str) -> TargetExp:
        return v

    def gen_list(self, l: List[TargetExp]) -> TargetExp:
        return "[list: " + ", ".join(l) + "]"

    def gen_tuple(self, t: List[TargetExp]) -> TargetExp:
        return "{" + "; ".join(t) + "}"

    @abstractmethod
    def gen_dict(self, keys: List[TargetExp], values: List[TargetExp]) -> TargetExp:
        """
        Translate a dictionary with keys and values
        """
        pass

    def gen_call(self, func: TargetExp, args: List[TargetExp]) -> TargetExp:
        return func + "(" + ", ".join(args) + ")"

    @abstractmethod
    def translate_prompt(self, name: str, args: List[ast.arg], returns: ast.expr, description: str) -> str:
        """
        Translate Python prompt.
        """
        pyret_docstring = "doc: ```" + re.sub(DOCSTRING_LINESTART_RE, "\n    ", description.strip()) + "```\n"

        # TODO: keep track of types? (see rust humaneval)
        def translate_arg(arg):
            return arg.arg + " :: " + translate_type(arg.annotation)

        arg_strings = []
        return_type = ""

        # FIXME: not sure why this is a try-except, copied from the rust humaneval
        try:
            arg_strings = [translate_arg(arg) for arg in args]
            return_type = " -> " + translate_type(returns) if returns else ""
        except Exception as e:
            print(e)
            return None

        arg_list = ", ".join(arg_strings)
        hashmap_datatype = hashmap_definition if needs_hashmap else ""

        return f"{hashmap_datatype}fun {name}({arg_list}){return_type}:\n    {pyret_docstring}"


    @abstractmethod
    def test_suite_prefix_lines(self, entry_point: str) -> List[str]:
        """
        This code goes at the start of the test suite.
        The entry_point is ???
        """
        # include the "end" because we use it as a stop-word
        return [
            "end",
            "", "",
            "check:",
            f"    candidate = {entry_point}"
            ]

    @abstractmethod
    def test_suite_suffix_lines(self) -> List[str]:
        """
        This code goes at the end of the test suite.
        """
        return ["end\n"]

    def deep_equality(self, left: TargetExp, right: TargetExp) -> str:
        # for some benchmarks, we want test suite to work with floats too
        # checks if the number is within 10^(-6)
        # works for non-numbers as regular equality
        return f"    {left} is-roughly {right}"

    def file_ext(self) -> str:
        return "arr"

    def no_completion_prompt_stub(self) -> str:
        """
        A default stub to create a syntactically valid translation in case of 
        not performing completion.
        """
        return "    ...\nend"


