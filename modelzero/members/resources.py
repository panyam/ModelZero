
from ipdb import set_trace
from flask_restplus import namespace
from modelzero.core.resources import BaseResource
from modelzero.utils import getLogger

log = getLogger(__name__)

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


def router_to_ns(router, ns, world):
    pass

def create_namespace(world):
    r = Router()
    r.POST(world.Members.create, 
           member = lambda self: self.params,
           viewer = lambda self: self.request_member)

    # /<....> has a get method
    r["<long:memberid>"].GET(world.Members.get,
        member = lambda self: self.params["memberid"],
        viewer = lambda self: self.request_member)

    # we also have a PUT method here
    r["<long:memberid>"].PUT(world.Members.update,
        member = lambda self: self.params["memberid"],
        viewer = lambda self: self.request_member)

    # And a delete method
    r["<long:memberid>"].DELETE(world.Members.delete,
        member = lambda self: self.params["memberid"],
        viewer = lambda self: self.request_member)

    ns = namespace.Namespace('members', description='Members API')
    router_to_ns(r, ns, world)
    return ns

def create_namespace2(world):
    ns = namespace.Namespace('members', description='Members API')
    @ns.route('/', resource_class_kwargs = {"world": world})
    class Members(BaseResource):
        @ns.doc(description="Create a new member given the member's fullname, email and phone number (optional).")
        def post(self):
            """
            Create a new member.
            """
            return world.Members.create(self.params, self.request_member)

    @ns.route('/<long:memberid>/', resource_class_kwargs = {"world": world})
    class Member(BaseResource):
        def get(self, memberid):
            return world.Members.get(memberid, self.request_member)

        def put(self, memberid):
            """ Update member data """
            return world.Members.update(memberid, self.params, self.request_member)

        def delete(self, memberid):
            """ Delete a member """
            return world.Members.delete(memberid, self.request_member)
    return ns, {k.__name__: k for k in [Members, Member]}
