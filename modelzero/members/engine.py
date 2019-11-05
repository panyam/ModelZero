
from ipdb import set_trace
import logging
from modelzero.core import errors, engine
from modelzero.core.store import Query
from modelzero.common.validators import *
from modelzero.common import engine
from modelzero.common.engine import EngineMethod
from modelzero.members.entities import Member, KEY_FIELD

class Engine(engine.Engine):
    ModelClass = Member

    @EngineMethod.ValidateParam("member", EnsureMissing(KEY_FIELD))
    @EngineMethod.ValidateParam("member", IgnoreFields("created_at"))
    @EngineMethod.ValidateParam("member", IgnoreFields("updated_at"))
    def create(self, member : Member, viewer : Member = None):
        # Ensure this email is not taken
        query = Query(Member)
        if "phone" in member:
            query.add_filter(phone__eq = member.phone)
        if "email" in member:
            query.add_filter(email__eq = member.email)

        if query.has_filters:
            members = self.table.fetch(query)
            if len(members) > 0:
                raise errors.ValidationError("Email or Phone Number is already used by another member.")

        member = self.table.put(member)
        return member
