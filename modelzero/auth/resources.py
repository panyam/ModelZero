
from modelzero.utils import getLogger, router, get_param 
from flask_restplus import namespace

import logging
log = logging.getLogger(__name__)

def kwarg_getter(key):
    return lambda self, *a, **kw: kw[key]
def param_getter(param):
    return lambda self, *a, **kw: get_param(self.params, param)
def get_request_member(self, *a, **kw):
    return self.request_member
def body_getter(self, *a, **kw):
    return self.params

def create_namespace(world):
    ns = namespace.Namespace('auth', description='Auth and Registration API', url_prefix = "/auth")
    r = router.Router()

    def set_channel_cookie(channel, res, *res_args, **res_kwargs):
        return channel, 200, {'Set-Cookie': channel.cookies}

    phone = r["phone"]
    phone_auth = world.Auth.get_authenticator("phone")
    phone["<string:action>"].GET(phone_auth.start_action,
                                 action = kwarg_getter("action"),
                                 phone = param_getter("phone")) \
            .doc("phone", "The phone number to perform auth on")
    phone["<string:action>"].POST(phone_auth.complete_action,
                                  action = kwarg_getter("action"),
                                  phone = param_getter("phone"),
                                  code = param_getter("phone"),
                                  memberbody = body_getter)                             \
            .doc("phone", "The phone number to perform auth on")                        \
            .doc("code", "The validation code sent to the phone number", "formData")    \
            .expects("modelzero.members.entities.Member")                               \
            .on_success(set_channel_cookie)

    """
    email = r["email"]
    email_auth = world.Auth.get_authenticator("email")
    email["<string:action>"].GET(email_auth.start_action,
            action = (kwarg_getter("action"),)
            param_getter).add_param("email", "The email to perform auth on")
    email["<string:action>"].POST(email_auth.complete_action,
            kwarg_getter("action"),
            param_getter).add_param("email", "The email to perform auth on").on_success(set_channel_cookie)
    """

    router.to_flask_ns(r, ns, world)
    return ns


def create_namespaces(world):
    ns = namespace.Namespace('auth', description='Auth and Registration API', url_prefix = "/auth")
    @ns.route("/phone/<string:action>/", resource_class_kwargs = {"world": world})
    class PhoneAuth(BaseResource):
        @property
        def authenticator(self):
            return world.Auth.get_authenticator("phone")

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
            return world.Auth.get_authenticator("email")

        def post(self, action):
            channel = self.authenticator.complete_action(action, self.params)
            return channel, 200, {'Set-Cookie': channel.cookies}
    return ns, {k.__name__: k for k in [PhoneAuth, EmailAuth]}
