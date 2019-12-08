
from ipdb import set_trace
import inspect
from inspect import signature
from modelzero.core import types
import typing, inspect
from typing import List, Union, Dict, Tuple
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

class Func(object):
    def __init__(self, fqn = None):
        self._param_default_values = {}
        self._fqn = None
        self._name = None
        if fqn and fqn.strip():
            parts = [f.strip() for f in fqn.split(".") if f.strip()]
            self._fqn = ".".join(parts)
            self._name = parts[-1]

    @property
    def fqn(self): return self._fqn

    @property
    def name(self): return self._name

    def has_default_value(self, param_name):
        return param_name in self._param_default_values

    def set_default_value(self, param_name, value):
        self._param_default_values[param_name] = value

    @property
    def return_type2(self): return self.func_type.return_type
    def has_param(self, name): return name in self.func_type.param_types
    def param(self, name): return self.func_type.param_types[name]
    @property
    def param_names(self): return self.func_type.param_types.keys()

    # Helper methods to create a "call" binding
    def call(self, **kwargs): return self(**kwargs) 
    def __call__(self, **kwargs):
        """ A derivation must also be callable since it is possible it is also used as a Transformer! """
        return Expr.as_apply(self, **kwargs)

class FuncExpr(Func):
    """ A function expression with an expression body that can be evaluated. """
    def __init__(self, fqn = None, **input_types : Dict[str, types.Type]):
        super().__init__(fqn)
        self._inputs = {k: ensure_type(v) for k, v in input_types.items()}
        self._body = None
        self._body_type = types.Type()

    def set_body(self, body : "Expr"):
        self._body = body
        self._body_updated = True

    @property
    def num_inputs(self): return len(self._inputs)

    @property
    def input(self):
        k = list(self._inputs.keys())[0]
        return k,self._inputs[k]

    def get_input(self, name : str) -> types.Type:
        return self._inputs[name]

    @property
    def body_type(self):
        if self._body_updated:
            # Update body_type
            self._body_updated = False
            self.infer_body_type()
            self._body_updated = False
        return self._body_type

    def infer_body_type(self):
        """ Kicks off inference of the body's type """
        to_be_implemented()

    @property
    def func_type(self):
        """ Returns the type that corresponds the result of the derivations """
        if self._func_type is None:
            self._func_type = types.Type.as_func_type(self._inputs, self.body_type)
        return self._func_type

class NativeFunc(Func):
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
        self.annotated_type = annotated_type
        self.inspected_sig = signature(self._func)
        self._inspected_type = None

    @property
    def target(self): return self._func

    @property
    def func_type(self):
        if not self._inspected_type:
            return_type = ensure_type(self.inspected_sig.return_annotation)

            param_types = {}
            for name,param in self.inspected_sig.parameters.items():
                # Ensure all required fields are covered in the API call
                if param.default is not inspect._empty:
                    self._param_default_values[name] = param.default
                param_types[name] = None
                if param.annotation and param.annotation is not inspect._empty:
                    annot = param.annotation
                    param_types[name] = ensure_type(annot)
            self._inspected_type = types.Type.as_func_type(param_types, return_type)

        if self.annotated_type:
            # Ensure there are no inconsistencies
            set_trace()
        return self._inspected_type

class New(object):
    def __init__(self, obj_type, children):
        self.obj_type = obj_type
        self.children = children

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

class FMap(object):
    def __init__(self, func_expr : "Expr", source_expr : "Expr"):
        self.func_expr = ensure_expr(func_expr)
        self.source_expr = ensure_expr(source_expr)

class Apply(object):
    def __init__(self, func_expr : Union[str, "Func"],
                 **kwargs_exprs : Dict[str, "Expr"]):
        assert issubclass(func_expr.__class__, Func)
        self.func_expr = ensure_expr(func_expr)
        self.kwargs_exprs = {k:ensure_expr(v) for k,v in kwargs_exprs.items()}

class Expr(TUnion):
    new = Variant("New")
    fmap = Variant("FMap")
    apply = Variant("Apply")
    fpath = Variant("FieldPath")
    func = Variant("FuncExpr")
    nfunc = Variant("NativeFunc")
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

    @case("new")
    def typeOfNew(self, new, query_stack : List["Query"]):
        return new.obj_type

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
    elif T is Apply: out.apply = input
    elif issubclass(T, FuncExpr): out.func = input
    elif issubclass(T, NativeFunc): out.nfunc = input
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

class Eval(CaseMatcher):
    """ Super class for expression evaluators. """
    __caseon__ = Expr

    @case("new")
    def execNew(self, new, env):
        set_trace()
        return new.obj_type

    @case("apply")
    def execApply(self, apply, env):
        set_trace()
        if apply.func_expr.is_nfunc:
            # Native function - call it?
            pass
        elif apply.func_expr.is_func:
            pass
        else:
            assert False, "Invalid function type"

    @case("fmap")
    def execFMap(self, fmap, env):
        set_trace()
        pass

    @case("fpath")
    def execFieldPath(self, fpath, env):
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
