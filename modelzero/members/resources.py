
from flask_restplus import namespace
from modelzero.utils import getLogger
from modelzero.apigen.apispec import API, Router, QueryParam, PathArg, Body, FieldPath, RequestMember

log = getLogger(__name__)

def create_api(world):
    r = Router()
    r.POST(world.Members.create, member = FieldPath(), viewer = RequestMember)

    # /<....> has a get method
    r["<int:memberid>"].GET(world.Members.get, member = PathArg("memberid"), viewer = RequestMember)

    # we also have a PUT method here
    r["<int:memberid>"].PUT(world.Members.update, member = PathArg("memberid"), viewer = RequestMember)

    # And a delete member
    r["<int:memberid>"].DELETE(world.Members.delete, member = PathArg("memberid"), viewer = RequestMember)
    return API("members", router = r, description = "Members API")

