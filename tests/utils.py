
from ipdb import set_trace
from modelzero import utils
from modelzero.members.entities import Member
import random, time

def create_test_world():
    from flask import Flask
    from modelzero import utils as neutils

    app = Flask(__name__)
    app.url_map.converters['long'] = neutils.LongConverter
    app.config['PROJECT_ID'] = "modelzero1"
    app.config['RESTPLUS_JSON'] = { "cls": neutils.NEJsonEncoder }

    from modelzero import world
    datastore = world.create_default_datastore(gae_app_id = "jukebox-7")
    theWorld = world.World(datastore)
    return theWorld

def mockResource(resClass, world = None):
    world = world or create_test_world()
    res = resClass(world = world)
    res._request_member = object()
    res._params = object()
    return res

def create_test_member(members, testid = None, testname = None, testemail = None):
    member_key = Member.Key(testid or int(time.time() * 1000))
    assert members.get_by_key(member_key, nothrow = True) == None
    fullname = testname or "Test Name {}".format(str(member_key))
    email = testemail or "{}@modelzero.com".format(str(member_key))
    phone = str(random.randint(1000000000,9999999999))
    year = random.randint(1970, 2000)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    date_of_birth = utils.ensure_date()("%d-%d-%d" % (year, month, day))
    member = Member(__key__ = member_key,
                    email = email, phone = phone,
                    date_of_birth = date_of_birth, fullname = fullname)
    members.put(member)
    assert member.getkey() == member_key
    assert member.fullname == fullname
    assert member.email == email
    assert member.phone == phone
    assert member.date_of_birth == date_of_birth
    return member

