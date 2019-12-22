
from ipdb import set_trace
from typing import List, Union, Dict, Tuple
from modelzero.core import exprs, bp
from taggedunion import Variant
from taggedunion import Union as TUnion, CaseMatcher, case

NativeNone = exprs.Native(None)
def ensure_native(val):
    if type(val) is not exprs.Native:
        val = exprs.Native(val)
    return val

class DFSEval(CaseMatcher):
    """ Super class for expression evaluators. """
    __caseon__ = exprs.Expr

    @case("let")
    def valueOfLet(self, let: exprs.Let, env) -> exprs.Native:
        expvals = {var: self(exp, env) for var,exp in let.mappings.items()}
        newenv = env.extend(**expvals)
        return self(let.body, newenv)

    @case("istype")
    def execIsType(self, istype: exprs.IsType, env) -> exprs.Native:
        result: exprs.Native = self(istype.expr, env)
        target_type = istype.type_or_expr
        if issubclass(target_type.__class__, exprs.Expr):
            target_type = self(target_type, env)
        return ensure_native(result.matches_type(target_type))

    @case("var")
    def execVar(self, var: exprs.Var, env) -> exprs.Native:
        value = env.get(var.name)
        return ensure_native(value)

    @case("ref")
    def execRef(self, ref: exprs.Ref, env) -> exprs.Native:
        # evaluate ref value if it is an Exprr only
        # otherwise we could have a value or a variable (in which case it is a ref to a var)
        if not ref.is_var:
            return self.__caseon__.as_ref(self(ref.expr, env)).ref
        else:
            # Return the ref cell as is - upto caller to use 
            # this reference and the value in it as it sees fit
            return ref

    @case("native")
    def execNative(self, native: exprs.Native, env) -> exprs.Native:
        return native

    @case("ifelse")
    def execIfElse(self, ifelse: exprs.IfElse, env) -> exprs.Native:
        result = self(ifelse.cond, env)
        return self(ifelse.exp1 if result else ifelse.exp2, env)

    @case("andexp")
    def execAndExpr(self, andexp: exprs.And, env) -> exprs.Native:
        for expr in andexp.exprs:
            result = self(expr, env)
            if not result.value: ensure_native(False)
        return ensure_native(True)

    @case("orexp")
    def execOrExpr(self, orexp: exprs.Or, env) -> exprs.Native:
        for expr in orexp.exprs:
            result = self(expr, env)
            if result.value: ensure_native(True)
        return ensure_native(False)

    @case("notexp")
    def execNotExpr(self, notexp: exprs.Not, env) -> exprs.Native:
        result = self(notexp.expr, env)
        return ensure_native(not result.value)

    @case("new")
    def execNew(self, new: exprs.New, env) -> exprs.Native:
        result = new.obj_type.record_class()
        return ensure_native(result)

    @case("func")
    def execFunc(self, func: exprs.Func, env) -> exprs.Native:
        return func.bind(env)

    @case("fmap")
    def execFMap(self, fmap, env) -> exprs.Native:
        assert len(fmap.func_expr.func.input_names) == 1
        boundfunc = self(fmap.func_expr, env)
        src : Native = self(fmap.src_expr, env)
        elements : list = src.value
        param = list(fmap.func_expr.func.input_names)[0]
        results = [self.apply_proc(boundfunc, {param: item}) for item in elements]
        set_trace()
        return exprs.Expr.as_native(results)

    @case("getter")
    def execGetter(self, getter: exprs.Getter, env) -> exprs.Native:
        src = self(getter.src_expr, env)
        if src is None:
            set_trace()
            return NativeNone
        if type(src) is not exprs.Native:
            set_trace()
        if src.value is None:
            # set_trace()
            return NativeNone
        value = getattr(src.value, getter.key)
        # if value is None: set_trace()
        return ensure_native(value)

    @case("setter")
    def execSetter(self, setter: exprs.Setter, env) -> exprs.Native:
        src = self(setter.src_expr, env)
        if src is not None:
            for key,value in setter.keys_and_values.items():
                result = self(value, env)
                setattr(src.value, key, result.value)
        return src

    @case("call")
    def execCall(self, call: exprs.Call, env) -> exprs.Native:
        boundfunc = self(call.operator, env)
        kwargs = {k: self(v, env) for k,v in call.kwargs.items()}
        return self.apply_proc(boundfunc, kwargs)

    def apply_proc(self, boundfunc : exprs.Function.BoundFunc, kwargs: Dict[str, exprs.Native]) -> exprs.Native:
        curr_func, curr_env = boundfunc.func, boundfunc.env

        # No partial application for now
        new_args = {}
        for input in curr_func.input_names:
            argval = None
            if input in kwargs:
                argval = kwargs[input]
            else:
                if curr_func.has_default_value(input):
                    argval = ensure_native(curr_func.get_default_value(input))
                else:
                    set_trace()
                    raise Exception(f"Value for arg '{input}' in function '{curr_func.fqn}' not found")
            new_args[input] = argval

        assert curr_func.body
        if type(curr_func.body) is exprs.Native:
            # We have a native function so call it
            target_func = curr_func.body.value
            new_args = {k:native.value for k,native in new_args.items()}
            return ensure_native(target_func(**new_args))
        newenv = curr_env.extend(**new_args)
        return self(curr_func.body, newenv)
