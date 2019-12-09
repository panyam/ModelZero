
from ipdb import set_trace
from typing import List, Union, Dict, Tuple
from modelzero.core import types, exprs, env
from modelzero.core.records import Record, Field
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

class FieldPath(object):
    def __init__(self, value : Union[str, List[str]]):
        if type(value) is str:
            value = [v.strip() for v in value.split("/") if v.strip()]
        self.parts = value

    def __getitem__(self, index):
        return self.parts[index]

class Selector(object):
    """ Commands that projects a particular field into a source field. """
    def __init__(self, name : str, source : "Expr"):
        self.target_name = name
        self.source_value = exprs.ensure_expr(source)

class Fragment(object):
    def __init__(self, query, condition : "Expr" = None, **kwargs):
        self.query = query
        self.condition = exprs.ensure_expr(condition)
        self.kwargs = {k:exprs.ensure_expr(v) for k,v in kwargs.items()}

class Bind(object):
    def __init__(self, name : str, source : "Expr", functor : "Expr"):
        self.target_name = name
        self.functor = exprs.ensure_expr(functor)
        self.source_value = exprs.ensure_expr(source)

class Command(TUnion):
    selector = Variant(Selector)
    fragment = Variant(Fragment)
    # binder = Variant(Bind)

class CommandProcessor(CaseMatcher):
    __caseon__ = Command

    @case("selector")
    def processSelector(self, selector : Selector,
                        curr_record : Record,
                        query_stack : List["Query"]):
        source_value = selector.source_value
        assert source_value is not None

        # See if this already exists and if types match - then OK
        rmeta = curr_record.__record_metadata__
        source_type = exprs.TypeInfer()(source_value, query_stack)
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
            expr_type = exprs.TypeInfer()(expr, query_stack)
            param_type = fragment.query.input_type(name)
            if expr_type != param_type:
                optional = True
                break
        query_rec = fragment.query.return_type.record_class
        for name, field in query_rec.__record_metadata__.items():
            cloned_field = field.clone()
            cloned_field.optional = field.optional or optional
            curr_record.register_field(name, cloned_field)

def InQuery(fqn = None, **input_types : Dict[str, types.Type]):
    out = Query(fqn, **input_types)
    out._is_inline = True
    return out

class Query(exprs.Func):
    def __init__(self, fqn = None, **input_types : Dict[str, types.Type]):
        super().__init__(fqn)
        for inname,intype in input_types.items():
            self.add_input(inname, intype)
            self.set_inferred_input_type(inname, intype)
        self._is_inline = False
        self._commands : List[Union[Selector, Fragment]] = []
        self._inferred_return_type = None

    @property
    def is_inline(self): return self._is_inline

    def include(self, query : "Query", **kwargs : Dict[str, "Expr"]):
        """ Includes one or all fields from the source type at the root level
        of this query
        """
        return self.add_command(Command.as_fragment(query, **kwargs))

    def include_if(self, condition : "Expr", query : "Query", **kwargs : Dict[str, "Expr"]):
        return self.add_command(Command.as_fragment(query, condition, **kwargs))

    def select(self, *selectors : List[Selector]):
        """ Selects a particular source field as a field in the current root. """
        for selector in selectors:
            if type(selector) is str:
                # we are doing a field copy
                if self.num_inputs == 1:
                    inname = list(self.input_names)[0]
                    intype = self.input_type(inname)
                    getter = exprs.Expr.as_getter(
                            exprs.Expr.as_var(inname),
                            selector)
                else:
                    set_trace()
                    # source_value = exprs.Expr.as_fpath(selector.target_name)
                self.add_command(Command.as_selector(selector, getter))
            elif type(selector) is tuple:
                assert len(selector) is 2
                self.add_command(Command.as_selector(selector[0], selector[1]))
        return self

    def add_command(self, cmd):
        self._commands.append(cmd)
        self._inferred_return_type = None
        self._func_expr = None
        return self

    @property
    def inferred_return_type(self):
        if self._inferred_return_type is None:
            self._eval_return_type([])
        return self._inferred_return_type

    @inferred_return_type.setter
    def inferred_return_type(self, value):
        self._inferred_return_type = None

    _counter = 1
    def _eval_return_type(self, query_stack : List["Query"]) -> types.Type:
        classdict = dict(__fqn__ = self.fqn)
        name = self.name
        if not name:
            name = f"Derivation_{self._counter}"
            self.__class__._counter += 1
            classdict["__fqn__"] = name
        record_class = types.RecordType.new_record_class(name, **classdict)
        self._inferred_return_type = types.Type.as_record_type(record_class)
        query_stack.append(self)
        for command in self._commands:
            CommandProcessor()(command, record_class, query_stack)
        query_stack.pop()

    @property
    def func_expr(self):
        if self._func_expr is None:
            if self.is_inline:
                set_trace()
                assert False, "func_expr can only be evalled for non-inlined queries"
            self._eval_func_expr([self])
        return self._func_expr

    def _eval_func_expr(self, query_stack : List["Query"]) -> exprs.Expr:
        root = exprs.Expr.as_new(self.return_type, [])
        for command in self._commands:
            NewMaker()(command, self.return_type, root, query_stack)
        self._func_expr = exprs.Expr.as_func(self.fqn, self._inputs,
                                             root,
                                             self.record_type)

class NewMaker(CaseMatcher):
    __caseon__ = Command

    @case("selector")
    def processSelector(self, selector : Selector,
                        curr_type : types.Type,
                        curr_object : exprs.Expr,
                        query_stack : List["Query"]):
        curr_object.children.append((selector.target_name, selector.source_value))

    @case("fragment")
    def processFragment(self, fragment : Fragment,
                        curr_type : types.Type,
                        curr_object : exprs.Expr,
                        query_stack : List["Query"]):
        for command in fragment.query._commands:
            self(command, curr_type, curr_object, query_stack)
