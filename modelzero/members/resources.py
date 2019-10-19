
from flask_restplus import namespace
from modelzero.utils import getLogger, router

log = getLogger(__name__)

def create_namespace(world):
    r = router.Router()
    r.POST(world.Members.create, 
           member = lambda self, *a, **kw: self.params,
           viewer = lambda self, *a, **kw: self.request_member)

    # /<....> has a get method
    r["<int:memberid>"].GET(world.Members.get,
        member = lambda self, *a, **kw: kw["memberid"],
        viewer = lambda self, *a, **kw: self.request_member)

    # we also have a PUT method here
    r["<int:memberid>"].PUT(world.Members.update,
        member = lambda self, *a, **kw: kw["memberid"],
        viewer = lambda self, *a, **kw: self.request_member)

    # And a delete method
    r["<int:memberid>"].DELETE(world.Members.delete,
        member = lambda self, *a, **kw: kw["memberid"],
        viewer = lambda self, *a, **kw: self.request_member)

    ns = namespace.Namespace('members', description='Members API')
    router.to_flask_ns(r, ns, world)
    return ns

