
from flask_restplus import namespace
from modelzero.utils import getLogger
from modelzero.apigen.apispec import API, Router, QueryParam, PathArg, Body, FieldPath, RequestMember

log = getLogger(__name__)

def create_default_routemap(world):
    return {
        "CreateMember": world.Members.create,
        "GetMemberDetails": world.Members.get,
        "UpdateMemberDetails": world.Members.update,
        "DeleteMember": world.Members.delete,
    }

def create_api():
    r = Router()
    r.POST("CreateMember")                      \
        .params(member = FieldPath(), viewer = RequestMember)

    # /<....> has a get method
    r["<int:memberid>"].GET("GetMemberDetails")     \
            .params(member = PathArg("memberid"), viewer = RequestMember)

    # we also have a PUT method here
    r["<int:memberid>"].PUT("UpdateMemberDetails")      \
            .params(member = PathArg("memberid"), viewer = RequestMember)

    # And a delete member
    r["<int:memberid>"].DELETE("DeleteMember")      \
            .params(member = PathArg("memberid"), viewer = RequestMember)
    return API("members", router = r, description = "Members API")

