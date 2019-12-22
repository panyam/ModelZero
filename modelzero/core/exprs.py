
from ipdb import set_trace
import inspect
from inspect import signature
from modelzero.core import types,bp,records
import typing, inspect
from typing import List, Union, Dict, Tuple
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

class Var(object):
    def __init__(self, name):
        if type(name) is not str:
            set_trace()
        self.name = name

    def __eq__(self, another):
        return self.name == another.name

    def __repr__(self):
        return "<Var(%s)>" % self.name

class Ref(object):
    """ This expression both captures a reference to a cell as well as a reference to a variable. """
    def __init__(self, expr_or_var):
        self.expr = expr_or_var

    @property
    def is_var(self):
        return type(self.expr) is str

    def __eq__(self, another):
        return self.expr == another.expr

class TupleExpr(object):
    def __init__(self, *children):
        self.children = list(children)

    def __eq__(self, another):
        if len(self.children) != len(another.children):
            return False
        for e1,e2 in zip(self.children, another.children):
            if e1 != e2: return False
        return True

    def __repr__(self):
        return "<Tuple(%s)>" % ", ".join(map(repr, self.children))

class Let(object):
    def __init__(self, **mappings: Dict[str, "Expr"]):
        self.mappings = mappings
        self.set_body(None)

    def set_body(self, body: "Expr") -> "Let":
        self.body = body
        return self

    def __eq__(self, another):
        return  len(self.mappings) == len(another.mappings) and \
                all(k in another.mappings and 
                    self.mappings[k] == another.mappings[k] 
                        for k in self.mappings.keys()) and \
                self.body == another.body

    def __repr__(self):
        mappings = ", ".join(f"{k} = {repr(v)}" for k,v in self.mappings.items())
        return f"<Let {mappings} in {repr(self.body)}"

class Or(object):
    def __init__(self, *exprs: List["Expr"]):
        self.exprs = exprs

    def __eq__(self, another):
        return  self.exprs == another.exprs

    def __repr__(self):
        return "<Or(%s)>" % ",".join(map(str, self.exprs))

class Not(object):
    def __init__(self, expr: "Expr"):
        self.expr = expr

    def __eq__(self, another):
        return  self.expr == another.expr

    def __repr__(self):
        return "<Not(%s)>" % str(self.expr)

class And(object):
    def __init__(self, *exprs: List["Expr"]):
        self.exprs = exprs

    def __eq__(self, another):
        return  self.exprs == another.exprs

    def __repr__(self):
        return "<And(%s)>" % ",".join(map(str, self.exprs))

class IfElse(object):
    def __init__(self, cond: "Expr", exp1: "Expr", exp2: "Expr"):
        self.cond = cond
        self.exp1 = exp1
        self.exp2 = exp2

    def __eq__(self, another):
        return  self.cond == another.cond and \
                self.exp1 == another.exp1 and \
                self.exp2 == another.exp2

    def __repr__(self):
        return "<If(%s) { %s } else { %s }>" % (str(self.cond), str(self.exp1), str(self.exp2))

class Function(object):
    """ Base Function interface. """

    class BoundFunc(object):
        """ A function statically bounded to an environment. """
        def __init__(self, func, env):
            self.func = func
            self.env = env

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

    def bind(self, env):
        return Function.BoundFunc(self, env)

    @property
    def fqn(self): return self._fqn

    @property
    def name(self): return self._name

    def has_default_value(self, param_name):
        return param_name in self._param_default_values

    def get_default_value(self, param_name):
        return self._param_default_values[param_name]

    def set_default_value(self, param_name, value):
        self._param_default_values[param_name] = value

    def add_input(self, inname: str, intype: types.Type = None):
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

    def has_input(self, name: str):
        return self.input_type(name) is not None

    @property
    def inferred_return_type(self):
        return self._inferred_return_type

    def set_inferred_return_type(self, value):
        self._inferred_return_type = value

    def set_annotated_input_type(self, inname: str, intype: types.Type):
        self.annotated_input_types[inname] = intype
        return self

    def set_inferred_input_type(self, inname: str, intype: types.Type):
        self.inferred_input_types[inname] = intype
        return self

    def annotated_input_type(self, inname: str) -> types.Type:
        return self.annotated_input_types.get(inname, None)

    def inferred_input_type(self, inname: str) -> types.Type:
        return self.inferred_input_types.get(inname, None)

    def input_type(self, inname: str) -> types.Type:
        out = self.annotated_input_type(inname) or \
                self.inferred_input_type(inname)
        if not out:
            set_trace()
            raise Exception(f"Input type '{inname}' is neither annotated or inferred")
        return out

    @property
    def return_type(self):
        return self.func_type.return_type

    """
    def input_type(self, inname: str) -> types.Type:
        out = self.annotated_input_type(inname) or \
                self.inferred_input_type(inname)
        if not out:
            raise Exception(f"Return type is neither annotated or inferred")
        return out
    """

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
                 params: List[Union[str, Tuple[str, types.Type]]] = None,
                 body: "Expr" = None):
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
        self._body = Native(self._func)
        super().__init__(f"{self._func.__module__}.{self._name}")
        self.analyse_function()

    @property
    def body(self) -> "Native":
        """ Returns the body expression of the function. """
        return self._body

    def analyse_function(self):
        """ Analyses the native function to extract type signature and defaults. """
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
    def __init__(self, obj_type):
        self.obj_type = obj_type

    def __eq__(self, another: "New"):
        return self.obj_type == another.obj_type

class Native(object):
    """ Native value expressions. """
    def __init__(self, value):
        T = type(value)
        if T not in (str, int, bool, float, tuple, list) and \
                not callable(value) and \
                not issubclass(T, records.Record) and \
                value is not None:
            set_trace()
            assert False
        self.value = value

    def matches_type(self, target_type):
        return issubclass(self.value.__class__, target_type.record_class)

class Getter(object):
    def __init__(self,src: "Expr", key: str):
        self.src_expr = src
        self.key = key

class Setter(object):
    def __init__(self, src: "Expr", **keys_and_values: Dict[str, "Expr"]):
        self.src_expr = src
        self.keys_and_values = keys_and_values

class IsType(object):
    def __init__(self, expr: "Expr", type_or_expr: Union["Expr", "Type"]):
        self.expr = expr
        self.type_or_expr = type_or_expr

class FMap(object):
    def __init__(self, func_expr: "Expr", src_expr: "Expr"):
        self.func_expr = ensure_expr(func_expr)
        self.src_expr = ensure_expr(src_expr)

class Call(object):
    def __init__(self, operator: Union[str, "Function", "Expr"],
                 **kwargs: Dict[str, "Expr"]):
        if issubclass(operator.__class__, Function):
            operator = Expr(func = operator)
        self.operator = ensure_expr(operator)
        self.kwargs = {k:ensure_expr(v) for k,v in kwargs.items()}

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
    new = Variant(New)
    let = Variant(Let)
    var = Variant(Var)
    ref = Variant(Ref)
    orexp = Variant(Or)
    andexp = Variant(And)
    notexp = Variant(Not)
    istype = Variant(IsType)
    ifelse = Variant(IfElse)
    fmap = Variant(FMap)
    call = Variant(Call)
    getter = Variant(Getter)
    setter = Variant(Setter)
    func = Variant(Function)
    native = Variant(Native)

    # Helper methods to create a "call" expression
    def __call__(self, **kwargs):
        """ A derivation must also be callable since it is possible it is also used as a Transformer! """
        return Expr.as_call(self, **kwargs)

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

class TypeInfer(CaseMatcher):
    __caseon__ = Expr

    @case("fmap")
    def typeOfFMap(self, fmap, query_stack: List["Query"]):
        func_expr_type = self(fmap.func_expr, query_stack)
        src_type = self(fmap.src_expr, query_stack)
        if not src_type:
            set_trace()
        assert src_type.is_type_app
        assert len(src_type.type_args) == 1, "Not sure how to deal with multiple type args in a functor"
        origin_type = src_type.origin_type
        return origin_type[func_expr_type]

    @case("new")
    def typeOfNew(self, new, query_stack: List["Query"]):
        return new.obj_type

    @case("notexp")
    def typeOfNot(self, notexp, query_stack: List["Query"]):
        from modelzero.core.custom_types import MZTypes
        return MZTypes.Bool

    @case("andexp")
    def typeOfAnd(self, andexp, query_stack: List["Query"]):
        from modelzero.core.custom_types import MZTypes
        return MZTypes.Bool

    @case("orexp")
    def typeOfOr(self, orexp, query_stack: List["Query"]):
        from modelzero.core.custom_types import MZTypes
        return MZTypes.Bool

    @case("istype")
    def typeOfIsType(self, istype, query_stack: List["Query"]):
        from modelzero.core.custom_types import MZTypes
        return MZTypes.Bool

    @case("ifelse")
    def typeOfIfElse(self, ifelse, query_stack: List["Query"]):
        set_trace()
        pass

    @case("var")
    def typeOfVar(self, var: Var, query_stack: List["Query"]):
        for query in query_stack:
            if query.has_input(var.name):
                return query.input_type(var.name)
        assert False

    @case("ref")
    def typeOfRef(self, ref: Ref, query_stack: List["Query"]):
        set_trace()
        assert False

    @case("call")
    def typeOfCall(self, call, query_stack: List["Query"]):
        return self(call.operator, query_stack)

    @case("getter")
    def typeOfGetter(self, getter: Getter, query_stack: List["Query"]):
        src_type = self(getter.src_expr, query_stack)
        rec_class = src_type.record_type.record_class
        field = rec_class.__record_metadata__[getter.key]
        return field.logical_type

    @case("setter")
    def typeOfSetter(self, setter: Setter, query_stack: List["Query"]):
        src_type = self(setter.src_expr, query_stack)
        return src_type

    @case("native")
    def typeOfNative(self, native, query_stack: List["Query"]):
        breakpoint()

    @case("let")
    def typeOfLet(self, let, query_stack: List["Query"]):
        breakpoint()

    @case("func")
    def typeOfFunc(self, func_expr, query_stack: List["Query"]):
        return func_expr.func_type.return_type

def ensure_type(t):
    if t in (None, inspect._empty):
        return None
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
            children = [ensure_type(ta) for ta in t.__args__]
            return types.Type.as_sum_type(None, *children)
        set_trace()
        a = 3
    try:
        return types.ensure_type(t)
    except Exception as exc:
        raise exc

def ensure_expr(input):
    if input is None: return Expr(native = Native(None))
    T = type(input)
    if T is Expr: return input
    if T is FMap: return Expr(fmap = input)
    elif T is Call: Expr(call = input)
    elif issubclass(T, Function): return Expr(func = input)
    elif T is str and input[0] == "$":
        parts = input[1:].split("/")
        if len(parts) == 1:
            return Expr(var = Var(parts[0]))
        else:
            getter = None
            for part in parts:
                if getter is None:
                    getter = Expr.as_var(parts[0])
                else:
                    getter = Expr.as_getter(getter, part)
            return getter
    else:
        return Expr(native = Native(input))

def load_func(func_or_fqn):
    return Expr(func = NativeFunc(func_or_fqn))
