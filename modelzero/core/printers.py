

from ipdb import set_trace
from typing import List, Union, Dict, Tuple
from modelzero.core import exprs
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

class Writer:
    def __init__(self):
        self.level = 0
        self.col = 0
        self.row = 0
        self.value = ""
        self.tab_size = 2

    def dump(self):
        print(self.value)

    def indent(self, delta = 1, end_with_nl = False):
        class Indenter:
            def __init__(self, writer, delta, end_with_nl):
                self.writer = writer
                self.delta = delta
                self.end_with_nl = end_with_nl

            def __enter__(self):
                writer = self.writer
                if writer.at_first_col:
                    # first col so add more spaces
                    indent_string = writer.indent_string(delta)
                    writer.value += indent_string
                    writer.col += len(indent_string)
                writer.level += self.delta
                return self

            def __exit__(self, exctype, value, tback):
                if exctype:
                    import traceback
                    traceback.print_tb(tback)
                    self.writer.level = 0
                    self.writer.nextline()
                    set_trace()
                    self.writer.write("EXCEPTION:")
                    self.writer.nextline()
                else:
                    writer = self.writer
                    if writer.at_first_col:
                        # first col so "remove" trailing spaces
                        indent_string = writer.indent_string(delta)
                        if writer.value.endswith(indent_string):
                            L = len(indent_string)
                            writer.value = writer.value[:-L]
                            writer.col -= L
                    writer.level -= self.delta
                    if self.end_with_nl: writer.nextline()
        return Indenter(self, delta, end_with_nl)

    @property
    def at_first_col(self):
        return self.col == self.tab_size * self.level

    def indent_string(self, level = None):
        level = level or self.level
        return " " * self.tab_size * level

    def writeln(self, text):
        self.write(text)
        self.nextline()

    def write(self, text):
        lines = text.split("\n")
        nlines = len(lines)
        for index,line in enumerate(lines):
            self.value += line
            self.col += len(line)
            if index != nlines - 1:  # we have more lines 
                self.nextline()
        return nlines

    def nextline(self):
        self.value += "\n"
        self.row += 1
        indent = self.indent_string()
        self.col = len(indent)
        self.value += indent

class PrettyPrinter(CaseMatcher):
    """ Exprression pretty printer. """
    __caseon__ = exprs.Expr

    @case("let")
    def eprintLet(self, let: exprs.Let, writer) -> exprs.Native:
        writer.writeln("let")
        with writer.indent():
            for var,expr in let.mappings.items():
                writer.write(f"{var} = ")
                self(expr, writer)
                writer.nextline()
        writer.writeln("in ")
        with writer.indent():
            self(let.body, writer)

    @case("istype")
    def eprintIsType(self, istype: exprs.IsType, writer) -> exprs.Native:
        writer.write("(")
        self(istype.expr, writer)
        writer.write(" isa ")
        if issubclass(istype.type_or_expr.__class__, exprs.Expr):
            self(istype.type_or_expr, writer)
        else:
            writer.write("T?")
        writer.write(")")

    @case("var")
    def eprintVar(self, var: exprs.Var, writer) -> exprs.Native:
        writer.write(f"${var.name}")

    @case("ref")
    def eprintRef(self, ref: exprs.Ref, writer) -> exprs.Native:
        writer.write("Ref<")
        self(ref.expr, writer)
        writer.write(">")

    @case("native")
    def eprintNative(self, native: exprs.Native, writer) -> exprs.Native:
        writer.write(f"Native({native.value})")

    @case("ifelse")
    def eprintIfElse(self, ifelse: exprs.IfElse, writer) -> exprs.Native:
        writer.write("if (")
        self(ifelse.cond, writer)
        writer.writeln(") {")
        with writer.indent():
            self(ifelse.exp1, writer)
        writer.writeln("} else {")
        with writer.indent(end_with_nl = True):
            self(ifelse.exp2, writer)
        writer.writeln("}")

    @case("block")
    def eprintBlock(self, block: exprs.Block, writer) -> exprs.Native:
        writer.writeln("{")
        with writer.indent(end_with_nl = True):
            for expr in block.exprs:
                self(expr, writer)
        writer.writeln("}")

    @case("notexp")
    def eprintNotExpr(self, notexp: exprs.Not, writer) -> exprs.Native:
        writer.write("(not ")
        self(notexp.expr, writer)
        writer.write(")")

    @case("andexp")
    def eprintAndExpr(self, andexp: exprs.And, writer) -> exprs.Native:
        writer.write("(")
        with writer.indent():
            for index,expr in enumerate(andexp.exprs):
                if index > 0: writer.write(" and ")
                self(expr, writer)
        writer.write(")")

    @case("orexp")
    def eprintOrExpr(self, orexp: exprs.Or, writer) -> exprs.Native:
        writer.write("(")
        with writer.indent():
            for index,expr in enumerate(orexp.exprs):
                if index > 0: writer.write(" or ")
                self(expr, writer)
        writer.write(")")

    @case("new")
    def eprintNew(self, new: exprs.New, writer) -> exprs.Native:
        writer.write(f"new {new.obj_type.record_class.__fqn__}()")

    def eprintFuncDecl(self, func : exprs.Func, writer):
        fqn = func.fqn or ''
        writer.write(f"func {fqn}(")
        for index,inname in enumerate(func.input_names):
            if index > 0: writer.write(", ")
            writer.write(f"{inname}: ")
            if func.has_input(inname):
                # intype = func.input_type(inname)
                writer.write("?")
            else:
                writer.write("?")
        writer.writeln(") {")
        with writer.indent(end_with_nl = True):
            if type(func.body) is exprs.Native:
                writer.write(repr(func.body.value))
            else:
                self(func.body, writer)
        writer.writeln("}")

    @case("func")
    def eprintFunc(self, func: exprs.Func, writer) -> exprs.Native:
        writer.write(f"{func.fqn}")

    @case("fmap")
    def eprintFMap(self, fmap, writer) -> exprs.Native:
        writer.write("FMAP($$)")

    @case("getter")
    def eprintGetter(self, getter: exprs.Getter, writer) -> exprs.Native:
        self(getter.src_expr, writer)
        writer.write(f".{getter.key}")

    @case("setter")
    def eprintSetter(self, setter: exprs.Setter, writer) -> exprs.Native:
        self(setter.src_expr, writer)
        with writer.indent():
            for key,value in setter.keys_and_values.items():
                writer.write(f".set({key}, ")
                self(value, writer)
                writer.writeln(f")")

    @case("call")
    def eprintCall(self, call: exprs.Call, writer) -> exprs.Native:
        self(call.operator, writer)
        writer.write("(")
        with writer.indent():
            for index,(k,v) in enumerate(call.kwargs.items()):
                if index > 0: writer.write(", ")
                self(v, writer)
        writer.write(")")
