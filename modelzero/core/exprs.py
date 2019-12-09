
from ipdb import set_trace
import inspect
from inspect import signature
from modelzero.core import types
import typing, inspect
from typing import List, Union, Dict, Tuple
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case


class Var(object):
    def __init__(self, name):
        if type(name) is not str:
            set_trace()
        self.name = name

    def printables(self):
        yield 0, "var %s" % self.name

    def __eq__(self, another):
        return self.name == another.name

    def __repr__(self):
        return "<Var(%s)>" % self.name

class TupleExpr(object):
    def __init__(self, *children):
        self.children = list(children)

    def printables(self):
        yield 0, "Tuple:"
        for c in self.children:
            yield 1, c.printables()

    def __eq__(self, another):
        if len(self.children) != len(another.children):
            return False
        for e1,e2 in zip(self.children, another.children):
            if e1 != e2: return False
        return True

    def __repr__(self):
        return "<Tuple(%s)>" % ", ".join(map(repr, self.children))

class Function(object):
    """ Base Function interface. """
    def __init__(self, fqn = None):
        self._param_default_values = {}
        self._fqn = None
        self._name = None
        if fqn and fqn.strip():
            parts = [f.strip() for f in fqn.split(".") if f.strip()]
            self._fqn = ".".join(parts)
            self._name = parts[-1]
        self._func_type = None
        self.input_names = set()
        self.annotated_input_types = {}
        self.inferred_input_types = {}
        self.annotated_return_type = None
        self.set_inferred_return_type(None)

    @property
    def fqn(self): return self._fqn

    @property
    def name(self): return self._name

    def has_default_value(self, param_name):
        return param_name in self._param_default_values

    def set_default_value(self, param_name, value):
        self._param_default_values[param_name] = value

    def add_input(self, inname : str, intype : types.Type = None):
        self._func_type = None
        self.input_names.add(inname)
        self.annotated_input_types[inname] = ensure_type(intype)
        self.inferred_input_types[inname] = None
        return self

    @property
    def body(self) -> "Expr":
        """ Returns the body expression of the function. """
        return None

    @property
    def num_inputs(self): return len(self.input_names)

    def has_input(self, name : str):
        return self.input_type(name) is not None

    @property
    def inferred_return_type(self):
        return self._inferred_return_type

    def set_inferred_return_type(self, value):
        self._inferred_return_type = value

    def set_annotated_input_type(self, inname : str, intype : types.Type):
        self.annotated_input_types[inname] = intype
        return self

    def set_inferred_input_type(self, inname : str, intype : types.Type):
        self.inferred_input_types[inname] = intype
        return self

    def annotated_input_type(self, inname : str) -> types.Type:
        return self.annotated_input_types.get(inname, None)

    def inferred_input_type(self, inname : str) -> types.Type:
        return self.inferred_input_types.get(inname, None)

    def input_type(self, inname : str) -> types.Type:
        out = self.annotated_input_type(inname) or \
                self.inferred_input_type(inname)
        if not out:
            raise Exception(f"Input type '{inname}' is neither annotated or inferred")
        return out

    @property
    def return_type(self):
        return self.func_type.return_type

    def input_type(self, inname : str) -> types.Type:
        out = self.annotated_input_type(inname) or \
                self.inferred_input_type(inname)
        if not out:
            raise Exception(f"Return type is neither annotated or inferred")
        return out

    @property
    def annotated_type(self):
        if self.annotated_return_type is None:
            return None
        for name in self.input_names:
            if self.annotated_input_type(name) is None: return None
        return types.Type.as_func_type(self.annotated_input_types,
                                       self.annotated_return_type)


    @property
    def inferred_type(self):
        if self.inferred_return_type is None:
            return None
        for name in self.input_names:
            if self.inferred_input_type(name) is None: return None
        return types.Type.as_func_type(self.inferred_input_types,
                                       self.inferred_return_type)

    @property
    def func_type(self):
        """ Returns the type that corresponds the result of the derivations """
        if self._func_type is None:
            self._func_type = self.annotated_type or self.inferred_type
        if not self._func_type:
            set_trace()
            raise Exception("Function type has neither been annotated nor inferred")
        return self._func_type

    # Helper methods to create a "call" expression
    def call(self, **kwargs): return self(**kwargs) 
    def __call__(self, **kwargs):
        """ A derivation must also be callable since it is possible it is also used as a Transformer! """
        return Expr.as_call(self, **kwargs)

class Func(Function):
    """ A function expression with an expression body that can be evaluated. """
    def __init__(self, fqn = None,
                 params : List[Union[str, Tuple[str, types.Type]]] = None,
                 body : "Expr" = None):
        super().__init__(fqn)
        for x in params or []: 
            if type(x) is tuple:
                pname,ptype = x
            else:
                pname,ptype = x,None
            self.add_input(pname, ptype)
        self._body = body

    @property
    def body(self) -> "Expr":
        """ Returns the body expression of the function. """
        return self._body

class NativeFunc(Function):
    """ Funcs that are "external" and not directly evaluatable by our executors. Typical system functions. """
    def __init__(self, func_or_fqn : Union[str, "function"],
                 annotated_type : types.Type = None):
        if type(func_or_fqn) is str:
            self._name = func_or_fqn
            self._func = resolve_fqn(func_or_fqn)
        else:
            self._func = func_or_fqn
            self._name = func_or_fqn.__name__
        super().__init__(f"{self._func.__module__}.{self._name}")
        self.analyse_function()

    @property
    def target(self): return self._func

    def analyse_function(self):
        self.inspected_sig = signature(self._func)
        self.set_inferred_return_type(ensure_type(self.inspected_sig.return_annotation))

        self.inferred_input_types = {}
        for name,param in self.inspected_sig.parameters.items():
            if param.default is not inspect._empty:
                self._param_default_values[name] = param.default
            self.inferred_input_types[name] = None
            if param.annotation and param.annotation is not inspect._empty:
                self.input_names.add(name)
                annot = param.annotation
                self.inferred_input_types[name] = ensure_type(annot)
            elif param.default is inspect._empty:   # since not optional - add it so type inference will fail unless annotated
                self.input_names.add(name)

class New(object):
    def __init__(self, obj_type, children):
        self.obj_type = obj_type
        self.children = children

class Literal(object):
    def __init__(self, value):
        self.value = value

class Getter(object):
    def __init__(self,source : "Expr", key : str):
        self.source_expr = source
        self.key = key

    def printables(self):
        yield 0, "Getter"
        yield 1, "Source:"
        yield 2, self.source_expr.printables()
        yield 1, "Key:"
        yield 2, self.key

class FMap(object):
    def __init__(self, func_expr : "Expr", source_expr : "Expr"):
        self.func_expr = ensure_expr(func_expr)
        self.source_expr = ensure_expr(source_expr)

class Call(object):
    def __init__(self, operator : Union[str, "Function"],
                 **kwargs : Dict[str, "Expr"]):
        assert issubclass(operator.__class__, Function)
        self.operator = ensure_expr(operator)
        self.kwargs = {k:ensure_expr(v) for k,v in kwargs.items()}

    def printables(self):
        yield 0, "Call"
        yield 1, "Operator:"
        yield 2, self.operator.printables()
        yield 1, "Args:"
        for argname,argexpr in self.kwargs.items():
            yield 2, argname, " = ", argexpr.printables()

    def __eq__(self, another):
        if self.operator != another.operator:
            return False
        if len(self.kwargs) != len(another.kwargs):
            return False
        for e1,e2 in zip(self.kwargs, another.kwargs):
            if e1 != e2:
                return False
        return True

    def __repr__(self):
        return "<Call (%s) in %s" % (self.operator, ", ".join(map(repr, self.arguments)))

class Expr(TUnion):
    new = Variant("New")
    var = Variant(Var)
    fmap = Variant("FMap")
    call = Variant("Call")
    getter = Variant(Getter)
    func = Variant("Func")
    nfunc = Variant("NativeFunc")
    literal = Variant("Literal")

    @property
    def annotated_type(self):
        if self._variant_value: return self._variant_value.annotated_type
        else: return None

    @property
    def inferred_type(self):
        if self._variant_value: return self._variant_value.inferred_type
        else: return None

    @annotated_type.setter
    def annotated_type(self, value):
        self._variant_value.annotated_type = value

    @inferred_type.setter
    def inferred_type(self, value):
        self._variant_value.inferred_type = value

    def printables(self):
        yield 0, self.variant_value.printables()

class TypeInfer(CaseMatcher):
    __caseon__ = Expr

    @case("fmap")
    def typeOfFMap(self, fmap, query_stack : List["Query"]):
        func_expr_type = self(fmap.func_expr, query_stack)
        source_type = self(fmap.source_expr, query_stack)
        if not source_type:
            set_trace()
        assert source_type.is_type_app
        assert len(source_type.type_args) == 1, "Not sure how to deal with multiple type args in a functor"
        origin_type = source_type.origin_type
        return origin_type[func_expr_type]

    @case("new")
    def typeOfNew(self, new, query_stack : List["Query"]):
        return new.obj_type

    @case("var")
    def typeOfVar(self, var : Var, query_stack : List["Query"]):
        for query in query_stack:
            if query.has_input(var.name):
                return query.input_type(var.name)

    @case("call")
    def typeOfCall(self, call, query_stack : List["Query"]):
        return self(call.operator, query_stack)

    @case("getter")
    def typeOfGetter(self, getter : Getter, query_stack : List["Query"]):
        source_type = self(getter.source_expr, query_stack)
        rec_class = source_type.record_type.record_class
        field = rec_class.__record_metadata__[getter.key]
        return field.logical_type

    @case("literal")
    def typeOfLiteral(self, literal, query_stack : List["Query"]):
        breakpoint()
        pass

    @case("func")
    def typeOfFunc(self, func_expr, query_stack : List["Query"]):
        return func_expr.func_type.return_type

    @case("nfunc")
    def typeOfNativeFunc(self, native_func, query_stack : List["Query"]):
        return native_func.func_type.return_type

def ensure_type(t):
    if t in (None, inspect._empty):
        return None
    from modelzero.core import types
    from modelzero.core.custom_types import MZTypes
    if t is str:
        return MZTypes.String
    if t is int:
        return MZTypes.Int
    if t is bool:
        return MZTypes.Bool
    if type(t) is typing._GenericAlias:
        if t.__origin__ == list:
            return MZTypes.List[ensure_type(t.__args__[0])]
        if t.__origin__ == dict:
            return MZTypes.Map[ensure_type(t.__args__[0]), ensure_type(t.__args__[1])]
        if t.__origin__ == typing.Union:
            if len(t.__args__) == 2 and type(None) in t.__args__:
                optional_of = t.__args__[0] or t.__args__[1]
                return MZTypes.Optional[ensure_type(optional_of)]
            else:
                children = [ensure_type(ta) for ta in t.__args__]
                return types.Type.as_sum_type(None, *children)
        set_trace()
        a = 3
    try:
        return types.ensure_type(t)
    except Exception as exc:
        raise exc

def ensure_expr(input):
    if input is None: return None
    T = type(input)
    if T is Expr: return input
    out = Expr()
    if T is FMap: out.fmap = input
    elif T is Call: out.call = input
    elif issubclass(T, Func): out.func = input
    elif issubclass(T, NativeFunc): out.nfunc = input
    elif T is str and input[0] == "$":
        parts = input[1:].split("/")
        if len(parts) == 1:
            out.var = Var(parts[0])
        else:
            getter = None
            for part in parts:
                if getter is None:
                    getter = Expr.as_var(parts[0])
                else:
                    getter = Expr.as_getter(getter, part)
            return getter
    else:
        if T not in (str, int, bool, float, tuple, list):
            set_trace()
            assert False
        out.literal = Literal(input)
    return out

class Eval(CaseMatcher):
    """ Super class for expression evaluators. """
    __caseon__ = Expr

    @case("new")
    def execNew(self, new, env):
        set_trace()
        return new.obj_type

    @case("var")
    def execVar(self, var : str, query_stack : List["Query"]):
        set_trace()
        pass

    @case("call")
    def execCall(self, call, env):
        set_trace()
        if call.func_expr.is_nfunc:
            # Native function - call it?
            pass
        elif call.func_expr.is_func:
            pass
        else:
            assert False, "Invalid function type"

    @case("fmap")
    def execFMap(self, fmap, env):
        set_trace()
        pass

    @case("getter")
    def execGetter(self, getter : Getter, query_stack : List["Query"]):
        set_trace()
        pass

    @case("literal")
    def execLiteral(self, literal, env):
        return literal.value

    @case("func")
    def execFunc(self, func_expr, env):
        set_trace()
        return literal.value

    @case("nfunc")
    def execNativeFunc(self, native_func, env):
        set_trace()
        return literal.value
