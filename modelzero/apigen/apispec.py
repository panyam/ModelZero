
import inspect
from inspect import signature
import typing
from ipdb import set_trace
from modelzero.core.resources import BaseResource
from modelzero.utils import get_param 
from modelzero.core import types

def ensure_type(t):
    if t is str:
        return types.StrType
    if t is int:
        return types.IntType
    if t is bool:
        return types.BoolType
    if type(t) is typing._GenericAlias:
        if t.__origin__ == list:
            return types.ListType[ensure_type(t.__args__[0])]
        if t.__origin__ == dict:
            return types.MapType[ensure_type(t.__args__[0]), ensure_type(t.__args__[1])]
        set_trace()
    try:
        return types.ensure_type(t)
    except Exception as exc:
        set_trace()
        raise exc

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
        if type(method_or_fqn) is str:
            self._name = method_or_fqn
            self._method = resolve_fqn(method_or_fqn)
        else:
            self._method = method_or_fqn
            self._name = method_or_fqn.__name__
        self.method_sig = signature(self._method)
        self.success_method = None
        self.error_method = None
        self.done_method = None
        self.param_docs = {}
        self.expected_type = None
        self.returned_type = None
        self.params(*args, **kwargs)
        self._return_type = None
        self._param_types = None

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
    def return_type(self):
        if not self._return_type:
            self._return_type = ensure_type(self.method_sig.return_annotation)
        if self._return_type is inspect._empty:
            return None
        return self._return_type

    @property
    def param_types(self):
        if self._param_types is None:
            self._param_types = {}
            for name,param in self.method_sig.parameters.items():
                # Ensure all required fields are covered in the API call
                if param.default is inspect._empty:
                    if name not in self.kwargs:
                        raise Exception(f"Method param '{name}' not provided in router method: {self.fqn}")
                self._param_types[name] = None
                if param.annotation and param.annotation is not inspect._empty:
                    annot = param.annotation
                    self._param_types[name] = ensure_type(annot)

            for name,param in self.kwargs.items():
                # Ensure name is actually accepted by the param
                if name not in self._param_types:
                    raise Exception(f"Parameter '{name}' not accepted by method '{self.fqn}'")
                ptype = ensure_type(self._param_types[name])
                if ptype is None:
                    raise Exception("Parameter '{name}' in '{self.fqn}' does not have a type annotation")
        return self._param_types

    @property
    def method(self):
        return self._method

    @property
    def fqn(self):
        return f"{self.method.__module__}.{self.name}"

    @property
    def name(self):
        return self._name

    def params(self, *args, **kwargs):
        """ Specification on the kind of parameters that can be accepted by this method.  These params should map to the params accepted by the handler/operation method. """
        self.args = args
        self.kwargs = kwargs
        self._param_types = None
        return self

    def expects(self, record_class):
        self.expected_class = record_class
        return self

    def returns(self, retclass):
        self.returned_class = retclass
        self._return_type = None
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
            result = self._method(*argvals, **kwargvals)
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
    ns = namespace.Namespace(api.name, description=api.description,
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
        return kwargs[key]

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
