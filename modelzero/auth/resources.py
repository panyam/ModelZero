
from ipdb import set_trace
from modelzero.core.resources import BaseResource
from modelzero.utils import get_param
from flask_restplus import namespace

import logging
log = logging.getLogger(__name__)

def create_namespace(world):
    ns = namespace.Namespace('auth', description='Auth and Registration API', url_prefix = "/auth")
    @ns.route("/phone/<string:action>/", resource_class_kwargs = {"world": world})
    class PhoneAuth(BaseResource):
        @property
        def authenticator(self):
            return world.Auth.get_authenticator("phone")

        def get(self, action):
            return self.authenticator.start_action(action, self.params)

        def post(self, action):
            channel = self.authenticator.complete_action(action, self.params)
            cookies = ["channel=%s;path=/" % channel.getkey().value, "ne_session_token=%s;path=/" % channel.session_token.decode()]
            return channel, 200, {'Set-Cookie': cookies}
        
    @ns.route("/email/<string:action>/", resource_class_kwargs = {"world": world})
    class EmailAuth(BaseResource):
        @property
        def authenticator(self):
            return world.Auth.get_authenticator("email")

        def post(self, action):
            channel = self.authenticator.complete_action(action, self.params)
            cookies = ["channel=%s;path=/" % channel.getkey().value, "ne_session_token=%s;path=/" % channel.session_token.decode()]
            return channel, 200, {'Set-Cookie': cookies}
    return ns, {k.__name__: k for k in [PhoneAuth, EmailAuth]}
