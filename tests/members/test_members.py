
from .. import utils as testutils
from .. utils import create_test_world

from ipdb import set_trace
from modelzero.members.entities import Member
from modelzero.core import errors
from modelzero.core.store import Query

TEST_PHONE = "+14084561234"

def test_members():
    engine = create_test_world().Members
    member = testutils.create_test_member(engine.table)
    now = member.getkey().first_part
    fullname, email, phone, dob = member.fullname, member.email, member.phone, member.date_of_birth
    engine.ensure_access(member, member, None)

    newfullname = "New Name"
    newemail = "email%d@modelzero.com" % now
    newphone = "1%s@modelzero.com" % phone
    newdob = "%d-%d-%d" % (dob.year + 1, dob.month, dob.day)

    # Now try and update one field at a time
    member = engine.update(member, dict(fullname = newfullname))
    assert member.fullname == newfullname

    ## Email and phone cannot be updated
    member = engine.update(member, dict(email = newemail))
    assert member.email == newemail

    member = engine.update(member, dict(phone = newphone))
    assert member.phone == newphone

    # Now delete the member
    engine.delete(member, member)
    assert engine.table.get_by_key(now, nothrow = True) is None

def test_create_member_with_dup_phone(mocker):
    engine = create_test_world().Members
    mocker.patch.object(engine.table, "fetch")
    try:
        member = engine.create(Member(fullname = "123", date_of_birth = "2017-10-10", phone = TEST_PHONE))
    except errors.ValidationError as ve:
        assert ve.message == "Email or Phone Number is already used by another member."
    engine.table.fetch.assert_called_once_with(Query(Member).add_filter(phone__eq = TEST_PHONE))

def test_create_member_with_dup_email(mocker):
    engine = create_test_world().Members
    mocker.patch.object(engine.table, "fetch")
    try:
        engine.create(Member(fullname = "123", date_of_birth = "2017-10-10", email = "test"))
    except errors.ValidationError as ve:
        assert ve.message == "Email or Phone Number is already used by another member."
    engine.table.fetch.assert_called_once_with(Query(Member).add_filter(email__eq = "test"))

def test_create_member_success(mocker):
    engine = create_test_world().Members
    mocker.patch.object(engine.table, "fetch")

    mput_last = engine.table.put
    def putter1(member):
        assert member.fullname == "fullname"
        assert member.email == "test"
    engine.table.put = putter1
    engine.create(Member(fullname = "fullname", date_of_birth = "2017-10-10", email = "test"))

    engine.table.put = mput_last
    engine.table.fetch.assert_called_once_with(Query(Member).add_filter(email__eq = "test"))
