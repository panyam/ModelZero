
import datetime
from modelzero.core.entities import *

class Channel(Entity):
    # The type of login - "phone", "username", "email", "google", "twitter", "facebook" etc
    login_type = StringField(required = True, indexed = True)

    # The login_type + login_id is unique and forms the ID of this entity
    login_id = StringField(required = True, indexed = True)

    # The verification string used if required by this channel
    verification_string = StringField()

    # When the verification was sent
    verification_sent_at = DateTimeField()

    # How long after the verification_sent_at is the verification valid for in seconds?
    verification_timeout = IntegerField(default = 60)

    # When this channel was verified - if this is None, then the channel has not been verified
    # and cannot be used for auth
    verified_at = DateTimeField()

    # Credentials for this entity (eg salted passwords etc)
    credentials = JsonField()

    # The session token that can be used to verify an api/user request on this channel
    session_token = BytesField()

    # Which member is this login channel tied to.  A login channel can only be tied to a single member,
    # but several login channels can point to the same member
    memberkey = KeyField("modelzero.members.entities.Member", indexed = True)

    def refresh_session_token(self):
        import binascii, os
        self.session_token = binascii.hexlify(os.urandom(64))
        return self

    @classmethod
    def key_fields(cls) -> List[str]:
        return ["login_type", "login_id"]

    def to_json(self, include_verification = False):
        out = {
            'login_type': self.login_type,
            'login_id': self.login_id,
            'session_token': self.session_token,
            'verified': self.is_verified,
            'member': self.memberkey
        }
        if include_verification:
            out['verification_string'] = self.verification_string
        return out

    @property
    def cookies(self):
        return ["channel=%s;path=/" % self.getkey().value,
                "mz_session_token=%s;path=/" % self.session_token.decode()]

    @property
    def verification_timedout(self):
        if self.verification_sent_at is None: return True
        return (datetime.datetime.utcnow() - self.verification_sent_at).total_seconds() > self.verification_timeout

    @property
    def is_verified(self):
        return self.verified_at is not None
