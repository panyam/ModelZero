
from modelzero.utils import getLogger, get_param 
from modelzero.apigen.apispec import API, Router, QueryParam, PathArg

import logging
log = logging.getLogger(__name__)

def create_default_routemap(world):
    return {
        "StartEmailRegistration": world.EmailAuth.start_action,
        "CompleteEmailRegistration": world.EmailAuth.complete_action,
    }

def create_api(world):
    r = Router()
    def set_channel_cookie(channel, res, *res_args, **res_kwargs):
        return channel, 200, {'Set-Cookie': channel.cookies}

    phone = r["phone"]
    phone["{action}"].GET(world.PhoneAuth.start_action)  \
            .params(action = PathArg("action"),
                    phone = QueryParam("phone"))            \
            .doc("phone", "The phone number to perform auth on")
    phone["{action}"].POST(world.PhoneAuth.complete_action)      \
            .params(action = PathArg("action"),
                    phone = QueryParam("phone"),
                    code = QueryParam("code"))                      \
            .doc("phone", "The phone number to perform auth on")    \
            .doc("code", "The validation code sent to the phone number", "formData")    \
            .on_success(set_channel_cookie)
    return API("auth", router = r, url_prefix = "/auth",
               description = "Auth and Registration API")

