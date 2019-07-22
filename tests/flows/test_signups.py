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

from modelzero.world import *

def test_signup_with_phone():
    """ Test signup with an email with no other pre-registrations. """
    world = create_test_world()
    members_engine, auth_engine = world.Members, world.Auth
    auth_ns, auth_resclasses = authresources.create_namespace(world)
    query = Query(Member).add_filter(phone__eq = TEST_PHONE)
    channel_key = "phone/%s" % TEST_PHONE
    channel = auth_engine.table.get_by_key(channel_key)
    if channel: auth_engine.table.delete(channel)

    PhoneAuth = auth_resclasses["PhoneAuth"]
    phone_auth = PhoneAuth(world = world, params = {"phone": TEST_PHONE})
    phone_auth.get("registration")
    channel = auth_engine.table.get_by_key(channel_key)
    assert channel.session_token is None
    pin = channel.verification_string

    phone_auth = PhoneAuth(world = world, params = {
                    'phone': TEST_PHONE,
                    'code': pin,
                    'fullname': "Test User",
                    'date_of_birth': "1990-01-02"})
    retchannel, code, headers = phone_auth.post("registration")
    channel = auth_engine.table.get_by_key(channel_key)
    assert retchannel == channel
    assert code == 200

    # Now login into these URLs
    phone_login = PhoneAuth(world = world, params = {
                            'phone': TEST_PHONE})
    assert phone_login.get("login")
    channel = auth_engine.table.get_by_key(channel_key)
    assert channel.session_token is not None
    pin2 = channel.verification_string

    phone_login = PhoneAuth(world = world, params = {
                            'phone': TEST_PHONE,
                            'code': pin2})
    retchannel, code, headers = phone_login.post("login")
    channel = auth_engine.table.get_by_key(channel_key)
    assert retchannel == channel
    assert code == 200

def test_signup_with_email():
    """ Test signup with an email with no other pre-registrations. """
    world = create_test_world()
    members_engine, auth_engine = world.Members, world.Auth
    auth_ns, auth_resclasses = authresources.create_namespace(world)
    query = Query(Member).add_filter(email__eq = TEST_EMAIL)
    channel_key = "email/%s" % TEST_EMAIL
    channel = auth_engine.table.get_by_key(channel_key)
    if channel: auth_engine.table.delete(channel)

    EmailAuth = auth_resclasses["EmailAuth"]
    email_auth = EmailAuth(world = world, params = {
                            'email': TEST_EMAIL,
                            'password': "password",
                            'fullname': "Test User",
                            'date_of_birth': "1990-01-02"})
    retchannel, code, headers = email_auth.post("registration")
    channel = auth_engine.table.get_by_key(channel_key)
    assert code == 200
    assert retchannel == channel
    assert channel.session_token is not None

    # Now do a login
    email_auth = EmailAuth(world = world, params = {
                            'email': TEST_EMAIL,
                            'password': "password"})
    retchannel, code, headers = email_auth.post("login")
    channel = auth_engine.table.get_by_key(channel_key)
    assert retchannel == channel
    assert code == 200

