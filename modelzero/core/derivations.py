
from ipdb import set_trace
from typing import List, Union, Dict, Tuple
from modelzero.core import types, functions
from modelzero.core.types import FieldPath
from modelzero.core.records import Record, Field
from modelzero.core.custom_types import MZTypes
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

def ensure_expr(input):
    if input is None: return None
    T = type(input)
    if T is Expr: return input
    out = Expr()
    if T is FMap: out.fmap = input
    elif T is Apply: out.apply = input
    elif T is Query: out.query = input
    elif T is functions.NativeFunction: out.native_func = input
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

class Expr(TUnion):
    fmap = Variant("FMap")
    apply = Variant("Apply")
    fpath = Variant("FieldPath")
    query = Variant("Query")
    native_func = Variant(functions.NativeFunction)
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

    @case("query")
    def typeOfQuery(self, query, query_stack : List["Query"]):
        return query.return_type

    @case("native_func")
    def typeOfNativeFunction(self, natfunc, query_stack : List["Query"]):
        return natfunc.return_type

class Selector(object):
    """ Commands that projects a particular field into a source field. """
    def __init__(self, name : str, source : Expr = None):
        self.target_name = name
        if source:
            source = ensure_expr(source)
        self.source_value = source

class Fragment(object):
    def __init__(self, query, condition : "Expr" = None, **kwargs):
        self.query = query
        self.condition = ensure_expr(condition)
        self.kwargs = {k:ensure_expr(v) for k,v in kwargs.items()}

class Command(TUnion):
    selector = Variant(Selector)
    fragment = Variant(Fragment)

class CommandProcessor(CaseMatcher):
    __caseon__ = Command

    @case("selector")
    def processSelector(self, selector : Selector,
                        curr_record : Record,
                        query_stack : List["Query"]):
        source_type = None
        source_value = selector.source_value
        if source_value is None:
            curr_query = query_stack[0]
            if curr_query.num_inputs == 1:
                inname,intype = curr_query.input
                source_value = Expr.as_fpath([inname, selector.target_name])
            else:
                source_value = Expr.as_fpath(selector.target_name)
        source_type = TypeOf()(source_value, query_stack)

        # See if this already exists and if types match - then OK
        rmeta = curr_record.__record_metadata__
        if selector.target_name in rmeta:
            field = rmeta[selector.target_name]
            curr_type = field.logical_type
            if source_type != logical_type:
                raise Exception(f"Duplicate field '{selector.target_name}' being added")
        new_field = Field(source_type)
        curr_record.register_field(selector.target_name, new_field)

    @case("fragment")
    def processFragment(self, fragment : Fragment,
                        curr_record : Record,
                        query_stack : List["Query"]):
        query_rec = fragment.query.func_type.return_type.record_class
        for name, field in query_rec.__record_metadata__.items():
            cloned_field = field.clone()
            if fragment.condition:
                cloned_field.optional = True
            curr_record.register_field(name, cloned_field)

class Literal(object):
    def __init__(self, value):
        self.value = value

class FMap(object):
    def __init__(self, func_expr : "Expr", source_expr : "Expr"):
        self.func_expr = ensure_expr(func_expr)
        self.source_expr = ensure_expr(source_expr)

class Apply(object):
    def __init__(self, func_expr : Union[str, "Function"],
                 **kwargs_exprs : Dict[str, "Expr"]):
        if hasattr(func_expr, "__call__") and not issubclass(func_expr.__class__, functions.Function):
            func_expr = functions.NativeFunction(func_expr)
        self.func_expr = ensure_expr(func_expr)

        remargs = func_expr.param_names

        self.kwargs_exprs = {}
        for k,v in kwargs_exprs.items():
            kwargs_exprs[k] = ensure_expr(v)
            {k:ensure_expr(v) for k,v in kwargs_exprs.items()}

class Query(functions.Function):
    def __init__(self, fqn = None, **input_types : Dict[str, types.Type]):
        super().__init__()
        self._inputs = {k: types.ensure_type(v) for k, v in input_types.items()}
        self._return_type = None
        self._func_type = None
        self._commands : List[Union[Selector, Fragment]] = []
        self._fqn = None
        self._name = None
        if fqn and fqn.strip():
            parts = [f.strip() for f in fqn.split(".") if f.strip()]
            self._fqn = ".".join(parts)
            self._name = parts[-1]

    @property
    def name(self): return self._name

    @property
    def fqn(self): return self._fqn

    @property
    def num_inputs(self): return len(self._inputs)

    @property
    def input(self):
        k = list(self._inputs.keys())[0]
        return k,self._inputs[k]

    def get_input(self, name : str) -> types.Type:
        return self._inputs[name]

    def apply(self, *commands : List["Command"]) -> "Command":
        self._commands.extend(commands)
        return self

    def include(self, query : "Query", **kwargs : Dict[str, Expr]):
        """ Includes one or all fields from the source type at the root level
        of this derivation.
        """
        self._commands.append(Command.as_fragment(query, **kwargs))
        return self

    def include_if(self, condition : "Expr", query : "Query", **kwargs : Dict[str, Expr]):
        self._commands.append(Command.as_fragment(query, condition, **kwargs))
        return self

    def exclude(self, source_field_path : FieldPath):
        """ Removes particular field paths. """
        pass

    def select(self, *selectors : List[Selector]):
        """ Selects a particular source field as a field in the current root. """
        for selector in selectors:
            if type(selector) is str:
                self._commands.append(Command.as_selector(selector))
            elif type(selector) is tuple:
                assert len(selector) is 2
                self._commands.append(Command.as_selector(selector[0], selector[1]))
        return self

    def __call__(self, **kwargs):
        """ A derivation must also be callable since it is possible it is also used as a Transformer! """
        return Apply(self, **kwargs)

    _counter = 1
    @property
    def func_type(self):
        """ Returns the type that corresponds the result of the derivations """
        if self._return_type is None:
            self._return_type = types.Type()
            self._func_type = types.Type.as_func_type(self._inputs, self._return_type)
            classdict = dict(__fqn__ = self.fqn)
            name = self.name
            if not name:
                name = f"Derivation_{self._counter}"
                self.__class__._counter += 1
            rec_class = types.RecordType.new_record_class(name, **classdict)
            rec_type = types.RecordType(rec_class)
            self._return_type.record_type = rec_type

            # now add fields from each command
            for command in self._commands:
                CommandProcessor()(command, rec_class, [self])
        return self._func_type
