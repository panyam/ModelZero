
from ipdb import set_trace
from typing import List, Union, Dict, Tuple
from modelzero.core import types
from taggedunion import Variant
from taggedunion import Union as TUnion

class Expr(TUnion):
    fmap = Variant("FMap")
    func = Variant("Func")
    query = Variant("Query")
    fpath = Variant("FieldPath")
    bind = Variant("Bind")

class Select(object):
    """ Commands that projects a particular field into a source field. """
    def __init__(self, *selectors : List[Union[str, Tuple[str, Expr]]]):
        self.selectors = selectors

class Include(object):
    def __init__(self, query, **kwargs):
        self.query = query
        self.kwargs = kwargs

class Command(TUnion):
    select = Variant(Select)
    include = Variant(Include)

class FieldPath(object):
    def __init__(self, value : Union[str, List[str]]):
        if type(value) is str:
            value = [v.strip() for v in value.split("/") if v.strip()]
        self.parts = value

class Func(object):
    """ Commands that produce evaluated fields. """
    def __init__(self, func_name : str, **func_kwargs : Dict[str, "Expr"]):
        super().__init__()
        self.func_name = func_name
        self.func_kwargs = func_kwargs

class FMap(object):
    def __init__(self, expr : "Expr"):
        self.expr = expr

class Bind(object):
    def __init__(self, func_expr : "Expr", **kwarg_exprs : Dict[str, "Expr"]):
        self.func_expr = func_expr
        self.kwarg_exprs = kwarg_exprs

class Query(object):
    def __init__(self, fqn = None, **input_types : Dict[str, types.Type]):
        self._inputs = {k: types.ensure_type(v) for k, v in input_types.items()}
        self._query_type = None
        self._name = self._fqn = None
        self._commands : List[Union[Select, Include]] = []
        if fqn and fqn.strip():
            parts = [f.strip() for f in fqn.split(".") if f.strip()]
            self._fqn = ".".join(parts)
            self._name = parts[-1]

    @property
    def name(self): return self._name

    @property
    def fqn(self): return self._fqn

    def get_input(self, name : str) -> types.Type:
        return self._inputs[name]

    def apply(self, *commands : List["Command"]) -> "Command":
        self._commands.extend(commands)
        return self

    def include(self, query : "Query", **kwargs : Dict[str, Expr]):
        """ Includes one or all fields from the source type at the root level
        of this derivation.
        """
        self._commands.append(Include(query, **kwargs))
        return self

    def exclude(self, source_field_path : FieldPath):
        """ Removes particular field paths. """
        pass

    def select(self, *selectors : List[Select]):
        """ Selects a particular source field as a field in the current root. """
        self._commands.extend(selectors)
        return self

    def __call__(self, **kwargs):
        """ A derivation must also be callable since it is possible it is also used as a Transformer! """
        return Bind(self, **kwargs)

    _counter = 1
    @property
    def query_type(self):
        """ Returns the type that corresponds the result of the derivations """
        if self._query_type is None:
            self._query_type = types.Type()
            classdict = dict(__fqn__ = self.fqn)
            name = self.name
            if not name:
                name = f"Derivation_{self._counter}"
                self._counter += 1
            rec_class = types.RecordType.new_record_class(name, **classdict)
            rec_type = types.RecordType(rec_class)
            self._query_type.record_type = rec_type
        return self._query_type
