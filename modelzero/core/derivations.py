
from ipdb import set_trace
from typing import List, Union, Dict, Tuple
from modelzero.core import types, functions
from modelzero.core.records import Record, Field
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

def ensure_expr(input):
    T = type(input)
    if T is Expr: return input
    out = Expr()
    if T is FMap: out.fmap = input
    elif T is Apply: out.apply = input
    elif T is Query: out.query = input
    elif T is FieldPath: out.fpath = input
    elif T is str and input[0] == "$":
        # create field path
        out.fpath = FieldPath(input[1:])
    else:
        out.literal = Literal(input)
    return out

class Expr(TUnion):
    fmap = Variant("FMap")
    apply = Variant("Apply")
    fpath = Variant("FieldPath")
    literal = Variant("Literal")

class TypeOf(CaseMatcher):
    __caseon__ = Expr

    @case("fmap")
    def typeOfFMap(self, fmap, query_stack : List["Query"]):
        return self(apply.func_expr, query_stack)

    @case("apply")
    def typeOfApply(self, apply, query_stack : List["Query"]):
        func_expr_type = self(apply.func_expr, query_stack)
        set_trace()
        func_argr_type = self(apply.func_expr, query_stack)

    @case("fpath")
    def typeOfFieldPath(self, fpath, query_stack : List["Query"]):
        set_trace()
        pass

    @case("literal")
    def typeOfLiteral(self, literal, query_stack : List["Query"]):
        set_trace()
        pass

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
        self.kwargs = kwargs

class Command(TUnion):
    selector = Variant(Selector)
    fragment = Variant(Fragment)

class CommandProcessor(CaseMatcher):
    __caseon__ = Command

    @case("selector")
    def processSelector(self, selector : Selector,
                        curr_record : Record,
                        query_stack : List["Query"]):
        curr_query = query_stack[0]
        source_type = None
        if selector.source_value is None:
            # Get it from the target type 
            # what if there are multiple target types?
            if curr_query.num_inputs != 1:
                raise Exception("Number of query inputs is not 1.  Source value for selector required")
            input = curr_query.input
            if input.is_record_type:
                source_type = input.record_class.__record_metadata__[selector.target_name].logical_type
            elif input.is_union_type:
                set_trace()
            else:
                raise Exception(f"Selector field '{selector.target_name}' must index a record or a union")
        else:
            # The type of the expression is the selector's type
            source_type = TypeOf()(selector.source_value, query_stack)

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
    def processFragment(self, selector : Selector,
                        curr_type : types.Type,
                        query_stack : List["Query"]):
        curr_query = query_stack[0]
        set_trace()
        pass

class Literal(object):
    def __init__(self, value):
        self.value = value

class FieldPath(object):
    def __init__(self, value : Union[str, List[str]]):
        if type(value) is str:
            value = [v.strip() for v in value.split("/") if v.strip()]
        self.parts = value

class FMap(object):
    def __init__(self, func_expr : "Expr", **kwargs_exprs : Dict[str, "Expr"]):
        self.func_expr = ensure_expr(func_expr)
        self.kwargs_exprs = {k:ensure_expr(v) for k,v in kwargs_exprs.items()}

class Apply(object):
    def __init__(self, func_expr : Union[str, "Function"],
                 **kwargs_exprs : Dict[str, "Expr"]):
        if hasattr(func_expr, "__call__") and not issubclass(func_expr.__class__, functions.Function):
            func_expr = functions.NativeFunction(func_expr)

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
        v = self._inputs.values()
        return list(v)[0]

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

    def include_if(self, query : "Query", condition : "Expr", **kwargs : Dict[str, Expr]):
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
                self._counter += 1
            rec_class = types.RecordType.new_record_class(name, **classdict)
            rec_type = types.RecordType(rec_class)
            self._return_type.record_type = rec_type

            # now add fields from each command
            for command in self._commands:
                CommandProcessor()(command, rec_class, [self])
        return self._func_type
