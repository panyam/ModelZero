
from ipdb import set_trace
import typing, inspect
from typing import List, Union, Dict, Tuple
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

class FMap(object):
    def __init__(self, func_expr : "Expr", source_expr : "Expr"):
        self.func_expr = ensure_expr(func_expr)
        self.source_expr = ensure_expr(source_expr)

class Apply(object):
    def __init__(self, func_expr : Union[str, "Function"],
                 **kwargs_exprs : Dict[str, "Expr"]):
        assert issubclass(func_expr.__class__, Function)
        self.func_expr = ensure_expr(func_expr)
        self.kwargs_exprs = {}
        for k,v in kwargs_exprs.items():
            kwargs_exprs[k] = ensure_expr(v)
            {k:ensure_expr(v) for k,v in kwargs_exprs.items()}

class Function(object):
    def __init__(self):
        self._param_default_values = {}

    def has_default_value(self, param_name):
        return param_name in self._param_default_values

    def set_default_value(self, param_name, value):
        self._param_default_values[param_name] = value

    @property
    def return_type(self):
        return self.func_type.return_type

    def has_param(self, name):
       return name in self.func_type.param_types

    def param(self, name):
        return self.func_type.param_types[name]

    @property
    def param_names(self):
        return self.func_type.param_types.keys()

    def call(self, **kwargs):
        return self(**kwargs)

    def __call__(self, **kwargs):
        """ A derivation must also be callable since it is possible it is also used as a Transformer! """
        return Apply(self, **kwargs)

class Literal(object):
    def __init__(self, value):
        self.value = value

class FieldPath(object):
    def __init__(self, value : typing.Union[str, typing.List[str]]):
        if type(value) is str:
            value = [v.strip() for v in value.split("/") if v.strip()]
        self.parts = value

    def __getitem__(self, index):
        return self.parts[index]

class Expr(TUnion):
    fmap = Variant("FMap")
    apply = Variant("Apply")
    fpath = Variant("FieldPath")
    function = Variant("Function")
    literal = Variant("Literal")

class TypeOf(CaseMatcher):
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

    @case("apply")
    def typeOfApply(self, apply, query_stack : List["Query"]):
        return self(apply.func_expr, query_stack)

    @case("fpath")
    def typeOfFieldPath(self, fpath : FieldPath, query_stack : List["Query"]):
        hitquery = None
        for q in query_stack:
            if q.has_param(fpath[0]):
                hitquery = q
                break
        if hitquery is None:
            raise Exception(f"Field path start variable '{fpath[0]}' not an input to any query")

        param = q.param(fpath[0])
        return param.type_for_field_path(*fpath.parts[1:])

    @case("literal")
    def typeOfLiteral(self, literal, query_stack : List["Query"]):
        breakpoint()
        pass

    @case("function")
    def typeOfFunction(self, function, query_stack : List["Query"]):
        return function.return_type

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
    elif T is Apply: out.apply = input
    elif issubclass(input.__class__, Function): out.function = input
    elif T is FieldPath: out.fpath = input
    elif T is str and input[0] == "$":
        # create field path
        out.fpath = FieldPath(input[1:])
    else:
        if T not in (str, int, bool, float, tuple, list):
            set_trace()
            assert False
        out.literal = Literal(input)
    return out
