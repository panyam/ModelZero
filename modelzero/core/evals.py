
from ipdb import set_trace
from typing import List, Union, Dict, Tuple
from modelzero.core import exprs
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

class DFSEval(CaseMatcher):
    """ Super class for expression evaluators. """
    __caseon__ = exprs.Exp

    @case("let")
    def valueOfLet(self, let : exprs.Let, env) -> exprs.Native:
        expvals = {var: self(exp, env) for var,exp in let.mappings.items()}
        newenv = env.extend(**expvals)
        return self(let.body, newenv)

    @case("istype")
    def execIsType(self, istype : exprs.IsType, env) -> exprs.Native:
        result : exprs.Native = self(istype.expr, env)
        target_type = istype.type_or_expr
        if issubclass(target_type.__class__, exprs.Exp):
            target_type = self(target_type, env)
        return result.matches_type(target_type)

    @case("var")
    def execVar(self, var : exprs.Var, env) -> exprs.Native:
        return env.get(var.name)

    @case("ref")
    def execRef(self, ref : exprs.Ref, env) -> exprs.Native:
        # evaluate ref value if it is an Expr only
        # otherwise we could have a value or a variable (in which case it is a ref to a var)
        if not ref.is_var:
            return self.__caseon__.as_ref(self(ref.expr, env)).ref
        else:
            # Return the ref cell as is - upto caller to use 
            # this reference and the value in it as it sees fit
            return ref

    @case("native")
    def execNative(self, native : exprs.Native, env) -> exprs.Native:
        return native

    @case("ifelse")
    def execIfElse(self, ifelse : exprs.IfElse, env) -> exprs.Native:
        result = self(ifelse.cond, env)
        return self(ifelse.exp1 if result else ifelse.exp2, env)

    @case("andexp")
    def execAndExp(self, andexp : exprs.And, env) -> exprs.Native:
        result = self(andexp.exp1, env)
        if not result: return False
        return self(andexp.exp2, env)

    @case("orexp")
    def execOrExp(self, orexp : exprs.Or, env) -> exprs.Native:
        result = self(orexp.exp1, env)
        if result: return True
        return self(orexp.exp2, env)

    @case("new")
    def execNew(self, new : exprs.New, env) -> exprs.Native:
        result = new.obj_type.record_class()
        return result

    @case("func")
    def execFunc(self, func : exprs.Func, env) -> exprs.Native:
        return func.bind(env)

    @case("fmap")
    def execFMap(self, fmap, env) -> exprs.Native:
        set_trace()
        pass

    @case("getter")
    def execGetter(self, getter : exprs.Getter, env) -> exprs.Native:
        source = self(getter.source_expr, env)
        set_trace()
        if source is None: return None
        return getattr(source, getter.key)

    @case("setter")
    def execSetter(self, setter : exprs.Setter, env) -> exprs.Native:
        source = self(setter.source_expr, env)
        if source is not None:
            for key,value in setter.keys_and_values.items():
                value = self(value, env)
                setattr(source, key, value)
        return source

    @case("call")
    def execCall(self, call : exprs.Call, env) -> exprs.Native:
        boundfunc = self(call.operator, env)
        kwargs = {k: self(v, env) for k,v in call.kwargs.items()}
        return self.apply_proc(boundfunc, kwargs)

    def apply_proc(self, boundfunc, kwargs : Dict[str, exprs.Native]) -> exprs.Native:
        curr_func, curr_env = boundfunc.func, boundfunc.env

        # No partial application for now
        new_args = {}
        for input in curr_func.input_names:
            argval = None
            if input in kwargs:
                argval = kwargs[input]
            else:
                if curr_func.has_default_value(input):
                    argval = exprs.Native(curr_func.get_default_value(input))
                else:
                    set_trace()
                    raise Exception(f"Value for arg '{input}' in function '{curr_func.fqn}' not found")
            new_args[input] = argval

        assert curr_func.body
        if type(curr_func.body) is exprs.Native:
            # We have a native function so call it
            target_func = curr_func.body.value
            new_args = {k:native.value for k,native in new_args.items()}
            return exprs.Native(target_func(**new_args))
        newenv = curr_env.extend(**new_args)
        return self(curr_func.body, newenv)
