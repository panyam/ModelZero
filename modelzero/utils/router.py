
from ipdb import set_trace
from modelzero.core.resources import BaseResource

class RouterMethod(object):
    def __init__(self, method, *args, **kwargs):
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.success_method = None
        self.error_method = None
        self.done_method = None
        self.param_docs = {}
        self.expected_type = None
        self.returned_type = None

    def expects(self, model_class):
        self.expected_class = model_class
        return self

    def returns(self, retclass):
        self.returned_class = retclass
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
            result = self.method(*argvals, **kwargvals)
            if self.success_method:
                result = self.success_method(result, target, *target_args, **target_kwargs)
        except Exception as e:
            if self.error_method:
                result = self.error_method(result, target, *target_args, **target_kwargs)
            else:
                raise e
        return result

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

    def child(self, key):
        for prefix,router in self.children:
            if prefix == key:
                return router
        newroute = Router(parent = self)
        self.children.append((key, newroute))
        return newroute

    def POST(self, method, *args, **kwargs):
        return self.add_method("POST", method, *args, **kwargs)

    def PUT(self, method, *args, **kwargs):
        return self.add_method("PUT", method, *args, **kwargs)

    def DELETE(self, method, *args, **kwargs):
        return self.add_method("DELETE", method, *args, **kwargs)

    def GET(self, method, *args, **kwargs):
        return self.add_method("GET", method, *args, **kwargs)

    def add_method(self, http_method, method, *args, **kwargs):
        rm = RouterMethod(method, *args, **kwargs)
        self.methods[http_method.upper()] = rm
        return rm

def to_flask_ns(router, ns, world, prefix = ""):
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
        to_flask_ns(child, ns, world, next)
