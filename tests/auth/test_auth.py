
from ipdb import set_trace
import random
import datetime
import binascii, hashlib, os

from .. utils import create_test_world
import modelzero
from modelzero.core import errors
from modelzero.members.entities import Member
from modelzero.auth.entities import Channel
from modelzero.auth.engine import *

TEST_PHONE = "+14084561234"
TEST_EMAIL = "test@email.com"

def create_test_engine():
    memberengine = create_test_world().Members

    from modelzero.auth.engine import AuthEngine, PhoneAuthenticator, EmailAuthenticator
    authengine = AuthEngine(datastore, memberengine)
    authengine.add_authenticator("email", EmailAuthenticator(authengine))
    authengine.add_authenticator("phone", PhoneAuthenticator(authengine))
    return authengine

def test_get_channel_create_on_missing(mocker):
    engine = create_test_world().AuthEngine
    mocker.spy(engine.table, "get_by_key")
    login_type, login_id = "phone", TEST_PHONE
    test = engine.get_channel(login_type, login_id, create = True, ensure_member = False)
    channel_key = "%s/%s" % (login_type, login_id)
    engine.table.get_by_key.assert_called_once_with(channel_key)

def test_get_channel_throws_unauthorized_on_missing(mocker):
    engine = create_test_world().AuthEngine
    mocker.spy(engine.table, "get_by_key")

    login_type, login_id = "phone", TEST_PHONE
    channel_key = "%s/%s" % (login_type, login_id)
    try:
        test = engine.get_channel(login_type, login_id)
    except errors.Unauthorized as err:
        assert err.message == "Invalid user.  Please register first."
    engine.table.get_by_key.assert_called_once_with(channel_key)

def test_phone_start_login(mocker):
    engine = create_test_world().AuthEngine
    channel, test_phone, test_code = object(), TEST_PHONE, "12345"
    phone_auth = engine.get_authenticator("phone")
    mocker.patch.object(phone_auth, "validate_phone_pin")
    mocker.patch.object(engine, "get_channel", return_value = channel)
    phone_auth.complete_action("login", TEST_PHONE, test_code)
    phone_auth.validate_phone_pin.assert_called_once_with(channel, test_code, save = True)
    engine.get_channel.assert_called_once_with("phone", TEST_PHONE, create = False, ensure_member = True)

def test_phone_start_registration(mocker):
    engine = create_test_world().AuthEngine
    channel, test_phone, test_code = object(), TEST_PHONE, "12345"
    phone_auth = engine.get_authenticator("phone")
    mocker.patch.object(phone_auth, "validate_phone_pin")
    mocker.patch.object(engine, "create_member_for_channel")
    mocker.patch.object(engine, "get_channel", return_value = channel)

    phone_auth.complete_action("registration", test_phone, test_code)
    phone_auth.validate_phone_pin.assert_called_once_with(channel, test_code, save = True)
    engine.create_member_for_channel.assert_called_once_with(channel)
    engine.get_channel.assert_called_once_with("phone", TEST_PHONE, create = True, ensure_member = False)

def test_validate_phone_pin_verification_timedout(mocker):
    engine = create_test_world().AuthEngine
    phone_auth = engine.get_authenticator("phone")
    try:
        params = {'code': "123"}
        channel = Channel(verification_string = "123", verification_sent_at = datetime.datetime(2000,1,1,1,1,1))
        phone_auth.validate_phone_pin(channel, params)
        assert False
    except errors.ValidationError as ve:
        assert ve.message.startswith("Verification timed out.")

def test_validate_phone_pin_invalid_pin(mocker):
    engine = create_test_world().AuthEngine
    phone_auth = engine.get_authenticator("phone")
    try:
        params = {'code': "123"}
        channel = Channel(verification_string = "1234", verification_sent_at = datetime.datetime.utcnow())
        phone_auth.validate_phone_pin(channel, params)
        assert False
    except errors.ValidationError as ve:
        assert ve.message.startswith("Sent PIN and Entered PIN do not match.")

def test_validate_phone_psuccess(mocker):
    engine = create_test_world().AuthEngine
    phone_auth = engine.get_authenticator("phone")
    test_code = "123"
    randval = b"abcde"
    mocker.patch("os.urandom", return_value = randval)

    now = datetime.datetime.utcnow()
    channel = Channel(verification_string = "123", verification_sent_at = now)
    phone_auth.validate_phone_pin(channel, test_code)
    assert (channel.verified_at - now).total_seconds() >= 0
    assert channel.session_token == binascii.hexlify(randval)

def test_send_phone_code(mocker):
    engine = create_test_world().AuthEngine
    phone_auth = engine.get_authenticator("phone")
    mocker.patch("modelzero.utils.phone.send_sms")
    mocker.patch("random.randint")
    random.randint.return_value = 66666
    
    now = datetime.datetime.utcnow()
    testphone = TEST_PHONE
    channel = Channel(login_type = "phone", login_id = testphone)

    phone_auth.send_phone_code(channel, "%s")

    assert channel.verification_string == "66666"
    assert channel.verification_timeout == phone_auth.verification_timeout
    assert (channel.verification_sent_at - now).total_seconds() >= 0
    random.randint.assert_called_once_with(10000, 99999)
    modelzero.utils.phone.send_sms.assert_called_once_with(testphone, "66666")

####################################################################################
##                      Email Login and Registration Tests
####################################################################################

def test_email_start_login(mocker):
    engine = create_test_world().AuthEngine
    email_auth = engine.get_authenticator("email")
    login_type, login_id = "email", "a@b.com"
    channel_key = "%s/%s" % (login_type, login_id)
    testpassword = "password"
    testsalt = "salt".encode('utf-8')
    hash = email_auth.calc_hash(testsalt, testpassword)
    channel = Channel(login_type = login_type, login_id = login_id,
                      credentials = {'salt': testsalt, 'hash': hash})
    mocker.patch.object(engine, "get_channel", return_value = channel)
    try:
        email_auth.complete_action("login", login_id, "badpassword")
        assert False, "Should not be here"
    except errors.ValidationError as ve:
        assert ve.message == "Invalid username or password"

    out = email_auth.complete_action("login", login_id, testpassword)
    assert channel == out

def test_register_with_email_validation_errors(mocker):
    engine = create_test_world().AuthEngine
    email_auth = engine.get_authenticator("email")
    channel = Channel(verification_string = "12345", verification_sent_at = datetime.datetime(2000,1,1,1,1,1))
    try:
        email_auth.complete_action("registration", TEST_EMAIL, "1")
    except errors.ValidationError as ve:
        assert ve.message.startswith("Password too short.")

def test_register_with_email_success(mocker):
    engine = create_test_world().AuthEngine
    email_auth = engine.get_authenticator("email")
    channel = Channel(verification_string = "12345", verification_sent_at = datetime.datetime.utcnow())

    mocker.patch.object(engine, "create_member_for_channel", return_value = "hello")
    mocker.patch.object(engine, "get_channel", return_value = channel)
    out = email_auth.complete_action("registration", TEST_EMAIL, "password")
    engine.get_channel.assert_called_once_with("email", TEST_EMAIL, create = True, ensure_member = False)
    engine.create_member_for_channel.assert_called_once_with(channel)
