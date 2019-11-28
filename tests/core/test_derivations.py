
from ipdb import set_trace
from modelzero.core.derivations import Query, Func, Bind, FMap
from modelzero.core.types import Type
from modelzero.core.custom_types import MZTypes
from modelzero.core.records import *
from modelzero.core import custom_fields as fields

class Date(Record):
    day = fields.Field(MZTypes.Int)
    month = fields.Field(MZTypes.Int)
    year = fields.Field(MZTypes.Int)

class User(Record):
    id = fields.Field(MZTypes.String)
    firstName = fields.Field(MZTypes.String)
    lastName = fields.Field(MZTypes.String)
    name = fields.Field(MZTypes.String)
    created_at = fields.DateTimeField()
    birthday = fields.Field(Type.as_record_type(Date))
    friends = fields.ListField("User")

def test_derivation_init(mocker):
    d = Query(user = User)
    u = d.get_input("user")
    assert u.is_record_type
    assert u.record_class == User

    dt = d.query_type
    assert dt.is_record_type
    rc = dt.record_class
    assert rc

    rm = rc.__record_metadata__
    assert len(rm) == 0

def test_basic(mocker):
    """
        {
          me {
            id
            firstName
            lastName
            birthday {
              month
              day
            }
            friends {
              name
            }
          }
        }
    """
    d = Query(user = User).select(
            "id",
            "firstName",
            "lastName",
            ("birthday", Bind(Query(date = Date).select("month", "day"),
                              date = "$user/birthday")),
            ("friends", FMap(Query(friend = User).select("name")))
        )
    me = Query().select(
            ("me", Bind(d, user = Func("get_current_user")))
         )

def test_example_10(mocker):
    """
        https://graphql.github.io/graphql-spec/draft/#example-34b2d
        {
            user(id: 4) {
                id
                name
                profilePic(width: 100, height: 50)
            }
        }
    """
    d = Query(user = User).select(
            "id",
            "name",
            ("profilePic", Func("get_profile_pic", id = "$user/id", width = 100, height = 50))
        )
    out = Query().select(
            ("user", d(user = Func("get_user", id = 4)))
         )


def test_example_14(mocker):
    """
    https://graphql.github.io/graphql-spec/draft/#example-34435
    {
        user(id: 4) {
            id
            name
            smallPic: profilePic(size: 64)
            bigPic: profilePic(size: 1024)
        }
    }
    """
    d = Query(user = User).select(
            "id",
            "name",
            ("smallPic", Func("get_profile_pic", id = "$user/id", size = 64)),
            ("bigPic", Func("get_profile_pic", id = "$user/id", size = 1024))
        )
    out = Query().select(
            ("user", d(user = Func("get_user", id = 4)))
         )
