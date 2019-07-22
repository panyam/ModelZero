
from ipdb import set_trace
from modelzero.core import errors
from modelzero.core import engine
from modelzero.core.engine import EngineMethod
from modelzero.utils import get_param, phone, getLogger
from modelzero.members.entities import Member
from modelzero.auth.entities import Channel

import hashlib, binascii, random, datetime, os
import json, phonenumbers
log = getLogger(__name__)

class AuthEngine(engine.Engine):
    ModelClass = Channel
    def __init__(self, datastore, memberengine, dev_mode = None):
        super().__init__(datastore, dev_mode)
        self.memberengine = memberengine
        self.authenticators = {}

    def add_authenticator(self, name : str, auth : "Authenticator"):
        self.authenticators[name] = auth

    def get_authenticator(self, name : str):
        return self.authenticators.get(name, None)

    @EngineMethod
    def get_channel(self, login_type, login_id, create = False, ensure_member = True, nothrow = False):
        login_type = login_type.lower().strip()
        login_id = login_id.strip()
        if login_type == "phone":
            login_id = phone.validate_phone_number(login_id)
        channel_id = "%s/%s" % (login_type, login_id)
        channel = self.table.get_by_key(channel_id)
        if not channel and create:
            channel = Channel(login_type = login_type,
                              login_id = login_id)
            self.table.put(channel)
        if (not channel or channel.memberkey is None) and ensure_member and not nothrow:
            raise errors.Unauthorized("Invalid user.  Please register first.")
        return channel

    def create_member_for_channel(self, channel, params):
        """ Creates a member for a new login channel that does not yet have a member associated with it. """
        if channel.memberkey is not None:
            raise errors.ValidationError("Member is already registered for this login channel")

        member = Member().apply_patch(params)
        member = self.memberengine.table.put(member)
        channel.memberkey = member.getkey()
        if channel.memberkey is None:
            set_trace()
            assert False
        self.table.put(channel)
        return member

    def get_request_member(self, request, nothrow = False):
        """ Gets the login channel and member associated with the current request. """
        channel = self.get_channel_from_request(request)
        if not channel:
            if nothrow: return None
            raise errors.Unauthorized("Login user not found")

        # get the modelzero user corresponding to this
        if not channel.memberkey and not nothrow:
            raise errors.Unauthorized("Invalid login user.")
        return channel

    def get_channel_from_request(self, request):
        cookies = request.cookies
        channel_id = cookies.get("channel")
        channel = None if not channel_id else self.table.get_by_key(channel_id)
        print("Channel: ", channel)
        if channel:
            print("Session Token: ", channel.session_token)
            print("Cookies: ", cookies)
        if channel and channel.session_token and channel.session_token.decode() == cookies.get("ne_session_token", ""):
            return channel

        # Try out google signin last!
        from modelzero.auth import users
        curr_user = users.get_current_user()
        if curr_user:
            channel_id = "gae/" + curr_user.user_id()
            channel = self.table.get_by_key(channel_id)
            if not channel:
                channel = Channel(login_type = "gae",
                                  login_id = curr_user.user_id(),
                                  verified_at = datetime.datetime.utcnow(),
                                  credentials = {'email': curr_user.email()})
                self.table.put(channel)
            return channel

class Authenticator(object):
    """ Phone Login and Registration Methods """
    def __init__(self, authengine):
        self.authengine = authengine

    def start_action(self, action, params):
        pass

    def complete_action(self, action, params):
        pass

class PhoneAuthenticator(Authenticator):
    """ Phone Login and Registration Methods """
    def __init__(self, authengine, verification_timeout = 600):
        super().__init__(authengine)
        self.verification_timeout = verification_timeout

    def send_phone_code(self, channel, body_template):
        pin = str(random.randint(10000, 99999))
        channel.verification_string = pin
        channel.verification_sent_at = datetime.datetime.utcnow()
        channel.verification_timeout = self.verification_timeout
        self.authengine.table.put(channel)

        log.info("PIN Code: %s" % pin)
        phone.send_sms(channel.login_id, body_template % pin)
        if self.authengine.is_dev_mode:
            return pin
        return True

    def start_action(self, action, params):
        phone = get_param(params, "phone")
        channel = self.authengine.get_channel("phone", phone, create = action == "registration", ensure_member = action == "login")
        return self.start_phone_verification(channel, params)

    def complete_action(self, action, params):
        phone = get_param(params, "phone")
        assert phone is not None
        channel = self.authengine.get_channel("phone", phone, create = action == "registration", ensure_member = action == "login")
        self.validate_phone_pin(channel, params, save = True)
        if action == "registration":
            self.authengine.create_member_for_channel(channel, params)
        return channel

    def validate_phone_pin(self, channel, params, save = False):
        code = get_param(params, "code")
        if channel.verification_timedout:
            raise errors.ValidationError("Verification timed out.  Please kick off phone login again")
        if code != channel.verification_string:
            raise errors.ValidationError("Sent PIN and Entered PIN do not match.  Please try again.")
        channel.verified_at = datetime.datetime.utcnow()
        channel.refresh_session_token()
        if save: 
            self.authengine.table.put(channel)
        return channel

    def start_phone_verification(self, channel, params):
        if False and channel.is_verified:
            raise errors.NotAllowed("Number already taken.")
        return self.send_phone_code(channel, "Use the PIN '%s' to verify phone number.")

class EmailAuthenticator(Authenticator):
    """ Email Login and Registration Methods """
    def __init__(self, authengine, verification_timeout = 600):
        super().__init__(authengine)
        self.verification_timeout = verification_timeout

    def calc_hash(self, salt : bytes, password : str):
        splusp = salt + bytes(password.encode('utf-8'))   
        hash = binascii.hexlify(hashlib.sha256(splusp).digest())
        return hash

    def complete_action(self, action, params):
        email = get_param(params, "email")
        channel = self.authengine.get_channel("email", email, create = action == "registration", ensure_member = action == "login")
        if action == "login":
            salt = channel.credentials['salt']
            hash = channel.credentials['hash']
            password = get_param(params, "password").strip()
            inputhash = self.calc_hash(salt, password)
            if hash != inputhash:
                raise errors.ValidationError("Invalid username or password")
            channel.refresh_session_token()
            self.authengine.table.put(channel)
        else:
            password = get_param(params, "password").strip()
            self.update_password(channel, password)
            self.authengine.create_member_for_channel(channel, params)
        return channel

    def update_password(self, channel, password, save = False):
        if len(password) < 8:
            raise errors.ValidationError("Password too short.  Must be atleast 8 characters") 
        salt = binascii.hexlify(os.urandom(128))
        hash = self.calc_hash(salt, password)
        channel.credentials = {'salt': salt, 'hash': hash}
        channel.verification_string = binascii.hexlify(os.urandom(256))
        channel.verification_sent_at = datetime.datetime.utcnow()
        channel.verification_timeout = self.verification_timeout
        channel.refresh_session_token()
        if save: self.authengine.table.put(channel)
        return channel

class GAEAuthEngine(AuthEngine):
    def finish_gae_registration(self, request, params):
        channel = self.get_channel_from_request(request)
        if not channel:
            raise errors.Unauthorized("Not logged in a valid GAE session")
        member = self.memberengine.create(resutils.RequestParamSource(request))
        channel.memberkey = member.getkey()
        self.table.put(channel)
        return channel
