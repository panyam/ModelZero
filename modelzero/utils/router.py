
from ipdb import set_trace
from modelzero.core.resources import BaseResource

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
        self.methods[http_method.upper()] = {
            "method": method,
            "args": args,
            "kwargs": kwargs
        }
        return self

def to_flask_ns(router, ns, world, prefix = ""):
    if router.methods:
        # if we have atleast one method, then create a "class"
        methods = {}
        for mname, mdata in router.methods.items():
            def themethod(self, *args, **kwargs):
                argvals = [arg(self, *args, **kwargs) for arg in mdata['args']]
                kwargvals = {k:v(self, *args, **kwargs) for (k,v) in mdata['kwargs'].items()}
                return mdata['method'](*args, **kwargs)
            methods[mname.lower()] = themethod

        newclass = type("RouterClass", (BaseResource,), methods)
        ns.add_resource(newclass, prefix,
                        resource_class_kwargs = {"world": world})

    for child_prefix,child in router.children:
        if prefix.endswith("/") or child_prefix.startswith("/"):
            next = prefix + child_prefix
        else:
            next = prefix + "/" + child_prefix
        to_flask_ns(child, ns, world, next)
