
from ipdb import set_trace
from typing import List, Union, Dict, Tuple
from modelzero.core import types, functions
from modelzero.core import exprs
from modelzero.core.records import Record, Field
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

class Selector(object):
    """ Commands that projects a particular field into a source field. """
    def __init__(self, name : str, source : "Expr" = None):
        self.target_name = name
        if source:
            source = exprs.ensure_expr(source)
        self.source_value = source

class Fragment(object):
    def __init__(self, query, condition : "Expr" = None, **kwargs):
        self.query = query
        self.condition = exprs.ensure_expr(condition)
        self.kwargs = {k:exprs.ensure_expr(v) for k,v in kwargs.items()}

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
            from modelzero.core.exprs import Expr
            curr_query = query_stack[0]
            if curr_query.num_inputs == 1:
                inname,intype = curr_query.input
                source_value = Expr.as_fpath([inname, selector.target_name])
            else:
                source_value = Expr.as_fpath(selector.target_name)
        source_type = exprs.TypeOf()(source_value, query_stack)

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
        optional = fragment.condition is not None
        # Another way this can be optional is if the arguments accepted
        # by the fragment are a subclass of the actual argument being passed
        # eg:
        # Fragment F1(a = A) { }
        # Fragment F2(b = B) { }
        # Query Q(item = AorB) {
        #   Include(F1, a = item)
        #   Include(F2, b = item)
        # }
        # Here a in F1 is a specific kind and its inclusion requires 
        # a cast from AorB to A.  This cast could fail, thereby failing
        # F1's inclusion.  In this case every member in F1 should be optional
        # in Q
        #
        # Going the otherway however is fine and wont incur an optionalling
        # Fragment F1(item = AorB) { }
        # Query Q(a= A) {
        #   Include(F1, item = a)
        # }
        #
        # Finally if there is a type mismatch (or casting is not possible)
        # It is an error.
        for name,expr in fragment.kwargs.items():
            expr_type = exprs.TypeOf()(expr, query_stack)
            param_type = fragment.query.param(name)
            if expr_type != param_type:
                optional = True
                break
        query_rec = fragment.query.func_type.return_type.record_class
        for name, field in query_rec.__record_metadata__.items():
            cloned_field = field.clone()
            cloned_field.optional = field.optional or optional
            curr_record.register_field(name, cloned_field)

class Query(exprs.Function):
    def __init__(self, fqn = None, **input_types : Dict[str, types.Type]):
        super().__init__()
        self._inputs = {k: exprs.ensure_type(v) for k, v in input_types.items()}
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

    def include(self, query : "Query", **kwargs : Dict[str, "Expr"]):
        """ Includes one or all fields from the source type at the root level
        of this query
        """
        self._commands.append(Command.as_fragment(query, **kwargs))
        return self

    def include_if(self, condition : "Expr", query : "Query", **kwargs : Dict[str, "Expr"]):
        self._commands.append(Command.as_fragment(query, condition, **kwargs))
        return self

    def select(self, *selectors : List[Selector]):
        """ Selects a particular source field as a field in the current root. """
        for selector in selectors:
            if type(selector) is str:
                self._commands.append(Command.as_selector(selector))
            elif type(selector) is tuple:
                assert len(selector) is 2
                self._commands.append(Command.as_selector(selector[0], selector[1]))
        return self

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
