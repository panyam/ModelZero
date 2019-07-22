
from flask_restplus import namespace
from modelzero.core.resources import BaseResource

import logging
log = logging.getLogger(__name__)

def create_namespace(world):
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
