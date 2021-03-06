
from ipdb import set_trace
from typing import List, Union, Dict, Tuple
from modelzero.core import types, exprs, env, bp
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
    """ Commands that projects a particular field into a src field. """
    def __init__(self, name : str, src : "Expr"):
        self.target_name = name
        self.src_value = exprs.ensure_expr(src)

class Fragment(object):
    def __init__(self, query : "Query", condition : "Expr" = None, **kwargs):
        self.query = query
        self.condition = None if not condition else exprs.ensure_expr(condition)
        self.kwargs = {k:exprs.ensure_expr(v) for k,v in kwargs.items()}

class Bind(object):
    def __init__(self, name : str, src : "Expr", functor : "Expr"):
        self.target_name = name
        self.functor = exprs.ensure_expr(functor)
        self.src_value = exprs.ensure_expr(src)

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
        src_value = selector.src_value
        assert src_value is not None

        # See if this already exists and if types match - then OK
        rmeta = curr_record.__record_metadata__
        src_type = exprs.TypeInfer()(src_value, query_stack)
        if selector.target_name in rmeta:
            field = rmeta[selector.target_name]
            curr_type = field.logical_type
            if src_type != curr_type:
                raise Exception(f"Duplicate field '{selector.target_name}' being added")
        new_field = Field(src_type)
        """
        # If all fields in the 
        if self._inferred_return_type.is_record_type:
            optional = False
            rmeta =  self._inferred_return_type.record_type.record_class.__record_metadata__
            for field_type in [v.logical_type for v in rmeta._fields.values()]:
                # if any field is *not* optional, then our return type cannot be optional
                if not field_type.is_optional_type:
                    optional = True
                    break
            if optional:
                self._inferred
                set_trace()
        """
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

class Query(exprs.Function):
    def __init__(self, fqn = None, **input_types : Dict[str, types.Type]):
        if not fqn:
            fqn = f"Derivation_{self._counter}"
            self.__class__._counter += 1
        super().__init__(fqn)
        for inname,intype in input_types.items():
            self.add_input(inname, intype)
            self.set_inferred_input_type(inname, intype)
        self._is_inline = False
        self._commands : List[Union[Selector, Fragment]] = []
        self._inferred_return_type = None
        self._func_body = None

    @property
    def is_inline(self): return self._is_inline

    def include(self, query : "Query", **kwargs : Dict[str, "Expr"]):
        """ Includes one or all fields from the src type at the root level
        of this query
        """
        return self.add_command(Command.as_fragment(query, **kwargs))

    def include_if(self, condition : "Expr", query : "Query", **kwargs : Dict[str, "Expr"]):
        return self.add_command(Command.as_fragment(query, condition, **kwargs))

    def select(self, *selectors : List[Selector]):
        """ Selects a particular src field as a field in the current root. """
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
                    # src_value = exprs.Expr.as_fpath(selector.target_name)
                self.add_command(Command.as_selector(selector, getter))
            elif type(selector) is tuple:
                assert len(selector) is 2
                self.add_command(Command.as_selector(selector[0], selector[1]))
        return self

    def add_command(self, cmd):
        self._commands.append(cmd)
        self._inferred_return_type = None
        self._func_body = None
        return self

    @property
    def inferred_return_type(self):
        if self._inferred_return_type is None:
            self._eval_return_type([])
        return self._inferred_return_type

    _counter = 1
    def _eval_return_type(self, query_stack : List["Query"]) -> types.Type:
        classdict = dict(__fqn__ = self.fqn)
        name = self.name
        record_class = types.RecordType.new_record_class(name, **classdict)
        self._inferred_return_type = types.Type.as_record_type(record_class)
        query_stack.append(self)
        for command in self._commands:
            CommandProcessor()(command, record_class, query_stack)
        query_stack.pop()

    @property
    def body(self):
        if self._func_body is None:
            if self.is_inline:
                set_trace()
                assert False, "func_body can only be evalled for non-inlined queries"
            self._eval_func_body([self])
        return self._func_body

    def _eval_func_body(self, query_stack : List["Query"]) -> exprs.Expr:
        self._func_body = exprs.Expr.as_new(self.return_type)
        for index,command in enumerate(self._commands):
            result = AttrSetter(command, self._func_body, query_stack)
            self._func_body = result.value
        # if at the end all we have is a new, then we have not set any fields
        # so can really delete this

class AttrSetter(CaseMatcher):
    __caseon__ = Command

    @case("selector")
    def processSelector(self, selector : Selector,
                        expr : exprs.Expr,
                        query_stack : List["Query"]):
        # how can we do optional setter chaining?

        # eg if we have 
        #   A.a = input.a
        #   A.b = input.b
        #   A.c = input.c
        #   ...
        #
        # and we want to do these conditionally, so something like:
        #
        # if (input.a) set(A, "a", input.a) else A
        # if (input.b) set(A, "b", input.b) else A
        # if (input.c) set(A, "c", input.c) else A
        # ...
        #
        # Problem here is that 
        return exprs.Expr.as_setter(expr,
                                   **{selector.target_name: selector.src_value})

    @case("fragment")
    def processFragment(self, fragment : Fragment,
                        expr : exprs.Expr,
                        query_stack : List["Query"]):
        # Need let expression here!!!
        """
        need to return something like:

        we need a "let_if a := ???
                          b := ???
                          c := ???
                          d := ???
                          in
                          body
                    else
                        else body
                    end

        or:

        if and([or(not fragment.condition, fragment.condition()),
                v1 is typeof(k1)
                v2 is typeof(k2)
                ....
                vn is typeof(kn)])
            exp = AttrSetter(AttrSetter(AttrSetter(exp1, cm1), cm2)...., cmdn)
        else
            exp
        end
        """
        elsebody = expr
        # Create the actual let body that applies the fragment
        let_mappings = {}
        let_body_conds = []
        for arg,argval in fragment.kwargs.items():
            if fragment.query.has_input(arg):
                argtype = fragment.query.input_type(arg)
                let_mappings[arg] = argval
                argvar = exprs.Expr.as_var(arg)
                let_body_conds.append(exprs.Expr.as_istype(argvar, argtype))

        setter_body = expr
        for index,command in enumerate(fragment.query._commands):
            result = AttrSetter(command, setter_body, query_stack)
            setter_body = result.value
        if len(let_body_conds) == 1:
            ifcond = let_body_conds[0]
        else:
            ifcond = exprs.Expr.as_andexp(*let_body_conds)
        let_body = exprs.Expr.as_ifelse(ifcond, setter_body, elsebody)
        let = exprs.Expr.as_let(**let_mappings)
        let.let.set_body(let_body)

        if not fragment.condition:
            return let

        # if we have a condition wrap the let in a conditional and return that
        return exprs.Expr.as_ifelse(fragment.condition, let, elsebody)
