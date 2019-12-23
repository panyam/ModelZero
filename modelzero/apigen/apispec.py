
import inspect
from inspect import signature
import typing
from ipdb import set_trace
from modelzero.core.resources import BaseResource
from modelzero.utils import get_param 
from modelzero.core import types
from modelzero.core import exprs
from modelzero.core.custom_types import *

class API(object):
    def __init__(self, name, router, description = "", url_prefix = ""):
        self.name = name
        self.url_prefix = url_prefix
        self.description = description
        self.router = router

class Router(object):
    def __init__(self, parent = None):
        self.parent = parent

        # List of "matches" and the associated methods on them
        # Each match is a "prefix" + child router
        self.children = []

        # The methods available upto this "part" of the prefix
        self.methods = {}

    def __getitem__(self, key):
        return self.child(key)

    @property
    def has_children(self):
        return len(self.methods) > 0

    def child(self, key):
        for prefix,router in self.children:
            if prefix == key:
                return router
        newroute = Router(parent = self)
        self.children.append((key, newroute))
        return newroute

    def POST(self, name, *args, **kwargs):
        return self.add_method("POST", name, *args, **kwargs)

    def PUT(self, name, *args, **kwargs):
        return self.add_method("PUT", name, *args, **kwargs)

    def DELETE(self, name, *args, **kwargs):
        return self.add_method("DELETE", name, *args, **kwargs)

    def GET(self, name, *args, **kwargs):
        return self.add_method("GET", name, *args, **kwargs)

    def add_method(self, http_method, name, *args, **kwargs):
        rm = Method(name, *args, **kwargs)
        self.methods[http_method.upper()] = rm
        return rm

class Method(object):
    def __init__(self, method_or_fqn, *args, **kwargs):
        self.function = exprs.NativeFunc(method_or_fqn)
        self.success_method = None
        self.error_method = None
        self.done_method = None
        self.param_docs = {}
        self.params(*args, **kwargs)

    @property
    def query_params(self):
        return {k: v for k,v in self.kwargs.items() if isinstance(v, QueryParam)}

    @property
    def patharg_params(self):
        return {k: v for k,v in self.kwargs.items() if isinstance(v, PathArg)}

    @property
    def body_param(self):
        for k,v in self.kwargs.items():
            if v == Body:
                return k,v
        return None, None

    @property
    def func_type(self):
        if self._func_type is None:
            self._func_type = self.function.func_type
            param_types = self._func_type.param_types
            # Make sure params that dont have default values 
            # are provided in kwargs
            for name,ptype in param_types.items():
                if not self.function.has_default_value(name) and name not in self.kwargs:
                    raise Exception(f"Method param '{name}' not provided in router method: {self.fqn}")
            for name,param in self.kwargs.items():
                # Ensure name is actually accepted by the param
                if name not in param_types:
                    raise Exception(f"Parameter '{name}' not accepted by method '{self.fqn}'")
                ptype = param_types[name]
                if ptype is None or not isinstance(ptype, Type):
                    raise Exception("Parameter '{name}' in '{self.fqn}' does not have a type annotation")
        return self._func_type

    @property
    def return_type(self):
        return self.func_type.return_type

    @property
    def param_types(self):
        return self.func_type.param_types

    @property
    def method(self):
        return self.function.target

    @property
    def fqn(self):
        return self.function.fqn

    @property
    def name(self):
        return self.function.name

    def params(self, *args, **kwargs):
        """ Specification on the kind of parameters that can be accepted by this method.  These params should map to the params accepted by the handler/operation method. """
        self.args = args
        self.kwargs = kwargs
        self._func_type = None
        return self

    def returns(self, retclass):
        self.returned_class = retclass
        self._func_type = None
        return self

    def expects(self, record_class):
        self.expected_class = record_class
        return self

    def doc(self, name, doc = "", source = "query"):
        self.param_docs[name] = (doc, source)
        return self

    def on_success(self, success_method):
        self.success_method = success_method
        return self

    def on_error(self):
        self.error_method = error_method
        return self

    def on_done(self):
        self.done_method = done_method
        return self

    def run(self, target, *target_args, **target_kwargs):
        argvals = [arg(target, *target_args, **target_kwargs) for arg in self.args]
        kwargvals = {k:v(target, *target_args, **target_kwargs) for (k,v) in self.kwargs.items()}
        try:
            func = self.function.body.value
            result = func(*argvals, **kwargvals)
            if self.success_method:
                result = self.success_method(result, target, *target_args, **target_kwargs)
        except Exception as e:
            if self.error_method:
                result = self.error_method(result, target, *target_args, **target_kwargs)
            else:
                raise e
        return result


def api_to_flask_ns(api, world):
    from flask_restplus import namespace
    ns = namespace.Namespace(api.name.lower(), description=api.description,
                             url_prefix = api.url_prefix)
    router_to_flask_ns(api.router, ns, world)
    return ns

def router_to_flask_ns(router, ns, world, prefix = ""):
    if router.methods:
        # if we have atleast one method, then create a "class"
        methods = {}
        def make_the_method(method):
            def themethod(self, *args, **kwargs):
                return method.run(self, *args, **kwargs)
            return themethod

        for name, method in router.methods.items():
            themethod = make_the_method(method)

            # Apply param docs
            for param_name, (param_doc, param_source) in method.param_docs.items():
                ns.param(param_name, description = param_doc, _in = param_source)(themethod)
            methods[name.lower()] = themethod

        newclass = type("RouterClass", (BaseResource,), methods)
        ns.add_resource(newclass, prefix,
                        resource_class_kwargs = {"world": world})

    for child_prefix,child in router.children:
        if prefix.endswith("/") or child_prefix.startswith("/"):
            next = prefix + child_prefix
        else:
            next = prefix + "/" + child_prefix
        router_to_flask_ns(child, ns, world, next)

class PathArg(object):
    def __init__(self, key):
        self.key = key

    def __call__(self, req, *args, **kwargs):
        return kwargs[self.key]

class FieldPath(object):
    def __init__(self, fp = None):
        self.field_path = fp

    def __call__(self, req, *args, **kwargs):
        return req.params

class QueryParam(object):
    def __init__(self, param):
        self.param = param

    def __call__(self, req, *args, **kwargs):
        return get_param(req.params, self.param)

def RequestMember(self, *a, **kw):
    return self.request_member

def Body(self, *a, **kw):
    return self.params
