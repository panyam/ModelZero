
from modelzero.utils import getLogger, router, get_param 
from modelzero.utils.router import QueryParam, PathArg, BodyFieldPath
from flask_restplus import namespace

import logging
log = logging.getLogger(__name__)

def create_namespace(world):
    ns = namespace.Namespace('auth', description='Auth and Registration API', url_prefix = "/auth")
    r = router.Router()

    def set_channel_cookie(channel, res, *res_args, **res_kwargs):
        return channel, 200, {'Set-Cookie': channel.cookies}

    phone_auth = world.PhoneAuth
    phone = r["phone"]
    phone["<string:action>"].GET("StartPhoneRegistration")  \
            .method(phone_auth.start_action)                \
            .params(action = PathArg("action"),
                    phone = QueryParam("phone"))            \
            .doc("phone", "The phone number to perform auth on")
    phone["<string:action>"].POST("CompletePhoneRegistration")      \
            .method(phone_auth.complete_action)                     \
            .params(action = PathArg("action"),
                    phone = QueryParam("phone"),
                    code = QueryParam("code"))                      \
            .doc("phone", "The phone number to perform auth on")    \
            .doc("code", "The validation code sent to the phone number", "formData")    \
            .on_success(set_channel_cookie)

    """
    email = r["email"]
    email_auth = world.EmailAuth
    email["<string:action>"].GET(email_auth.start_action,
            action = (PathArg("action"),)
            QueryParam).add_param("email", "The email to perform auth on")
    email["<string:action>"].POST(email_auth.complete_action,
            PathArg("action"),
            QueryParam).add_param("email", "The email to perform auth on").on_success(set_channel_cookie)
    """

    router.to_flask_ns(r, ns, world)
    return ns


def create_namespaces(world):
    ns = namespace.Namespace('auth', description='Auth and Registration API', url_prefix = "/auth")
    @ns.route("/phone/<string:action>/", resource_class_kwargs = {"world": world})
    class PhoneAuth(BaseResource):
        @property
        def authenticator(self):
            return world.PhoneAuth

        @ns.param("phone", "The phone number to perform auth on")
        def get(self, action):
            return self.authenticator.start_action(action,
                            phone = get_param(self.params, "phone"))

        @ns.expect(to_flask_model(Member))
        def post(self, action):
            channel = self.authenticator.complete_action(action = action,
                    phone = get_param(self.params, "phone"),
                    code = get_param(self.params, "code"),
                    memberbody = self.params)
            return channel, 200, {'Set-Cookie': channel.cookies}
        
    @ns.route("/email/<string:action>/", resource_class_kwargs = {"world": world})
    class EmailAuth(BaseResource):
        @property
        def authenticator(self):
            return world.EmailAuth

        def post(self, action):
            channel = self.authenticator.complete_action(action, self.params)
            return channel, 200, {'Set-Cookie': channel.cookies}
    return ns, {k.__name__: k for k in [PhoneAuth, EmailAuth]}
