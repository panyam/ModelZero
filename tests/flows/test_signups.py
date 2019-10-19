from .. utils import create_test_world

from ipdb import set_trace
import random, datetime
import binascii, hashlib, time
import requests, urllib
from modelzero.core import errors
from modelzero.core.store import Query
from modelzero.members.entities import Member
from modelzero.members.engine import Engine as MemberEngine
from modelzero.auth.entities import Channel
from modelzero.auth import resources as authresources
from modelzero.auth.engine import *

TEST_HOST = "http://localhost:8080"
TEST_PHONE = "+14084561234"
TEST_EMAIL = "test1@modelzero.com"

def test_signup_with_phone():
    """ Test signup with an email with no other pre-registrations. """
    world = create_test_world()
    members_engine, auth_engine = world.Members, world.AuthEngine
    query = Query(Member).add_filter(phone__eq = TEST_PHONE)
    channel_key = "phone/%s" % TEST_PHONE
    channel = auth_engine.table.get_by_key(channel_key)
    if channel: auth_engine.table.delete(channel)

    phone_auth = world.PhoneAuth
    phone_auth.start_action("registration", phone = TEST_PHONE)

    channel = auth_engine.table.get_by_key(channel_key)
    assert channel.session_token is None
    pin = channel.verification_string

    retchannel = phone_auth.complete_action("registration", phone = TEST_PHONE, code = pin)

    """
    phone_auth = PhoneAuth(world = world, params = {
                    'phone': TEST_PHONE,
                    'code': pin,
                    'fullname': "Test User",
                    'date_of_birth': "1990-01-02"})
    retchannel, code, headers = phone_auth.post("registration")
    """
    channel = auth_engine.table.get_by_key(channel_key)
    assert retchannel == channel

    # Now login into these users
    phone_auth.start_action("login", phone = TEST_PHONE)
    channel = auth_engine.table.get_by_key(channel_key)
    assert channel.session_token is not None
    pin2 = channel.verification_string

    retchannel = phone_auth.complete_action("login", phone = TEST_PHONE, code = pin2)
    channel = auth_engine.table.get_by_key(channel_key)
    assert retchannel == channel

def test_signup_with_email():
    """ Test signup with an email with no other pre-registrations. """
    world = create_test_world()
    members_engine, auth_engine = world.Members, world.AuthEngine
    query = Query(Member).add_filter(email__eq = TEST_EMAIL)
    channel_key = "email/%s" % TEST_EMAIL
    channel = auth_engine.table.get_by_key(channel_key)
    if channel: auth_engine.table.delete(channel)

    email_auth = world.EmailAuth
    retchannel = email_auth.complete_action("registration", email = TEST_EMAIL, password = "password")
    channel = auth_engine.table.get_by_key(channel_key)
    assert retchannel == channel
    assert channel.session_token is not None

    # Now do a login
    retchannel = email_auth.complete_action("login", email = TEST_EMAIL, password = "password")
    channel = auth_engine.table.get_by_key(channel_key)
    assert retchannel == channel

