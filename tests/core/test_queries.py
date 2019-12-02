
import typing
from modelzero.core.exprs import Apply, FMap
from modelzero.core.types import Type
from modelzero.core.queries import Query
from modelzero.core.functions import NativeFunction
from modelzero.core.custom_types import MZTypes
from modelzero.core.records import *
from modelzero.core import custom_fields as fields

def assert_has_fields(rec_type, fields : typing.List[str]):
    assert rec_type.is_record_type
    rmeta = rec_type.record_class.__record_metadata__
    assert rmeta.num_fields == len(fields)
    for f in fields:
        assert f in rmeta

class Date(Record):
    day = fields.Field(MZTypes.Int)
    month = fields.Field(MZTypes.Int)
    year = fields.Field(MZTypes.Int)

class UserRecord(Record):
    id = fields.Field(MZTypes.String)
    handle = fields.Field(MZTypes.String)
    firstName = fields.Field(MZTypes.String)
    lastName = fields.Field(MZTypes.String)
    name = fields.Field(MZTypes.String)
    created_at = fields.DateTimeField()
    birthday = fields.Field(Type.as_record_type(Date))
    friends = fields.ListField("User")
User = Type.as_record_type(UserRecord)

class PageRecord(Record):
    id = fields.Field(MZTypes.String)
    handle = fields.Field(MZTypes.String)
    url = fields.Field(MZTypes.URL)
Page = Type.as_record_type(PageRecord)

PageOrUser = Type.as_sum_type("PageOrUser", Page, User)

class FriendsRecord(Record):
    count = fields.Field(MZTypes.Int)
Friends = Type.as_record_type(FriendsRecord)

class LikersRecord(Record):
    count = fields.Field(MZTypes.Int)
Likers = Type.as_record_type(LikersRecord)

def get_user(id : int, handle : str = None) -> User:
    pass

def get_current_user() -> User:
    pass

def get_profile_pic(id : int, size : int = 100, width : int = 100, height : int = 100) -> str:
    pass

def get_friends(id : int, first : int = 10) -> typing.List[User]: pass

def get_mutual_friends(id : int, first : int = 10) -> MZTypes.List[User]: pass

def get_likers(id : int, first : int = 10) -> MZTypes.List[User]:
    pass

def get_profiles(handles : typing.List[str]) -> typing.List[typing.Union[User, Page]]:
    pass

GetUser = NativeFunction(get_user)
GetCurrentUser = NativeFunction(get_current_user)
GetProfilePic = NativeFunction(get_profile_pic)
GetFriends = NativeFunction(get_friends)
GetMutualFriends = NativeFunction(get_mutual_friends)
GetLikers = NativeFunction(get_likers)
GetProfiles = NativeFunction(get_profiles)

#### BEGIN Tests

def test_derivation_init(mocker):
    d = Query(user = User)
    u = d.get_input("user")
    assert u.is_record_type
    assert u.record_class == UserRecord

    dt = d.return_type
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
            ("birthday", Apply(Query(date = Date).select("month", "day"), date = "$user/birthday")),
            ("friends", FMap(Query(friend = User).select("name"), "$user/friends"))
        )
    out = Query().select( ("me", d(user = GetCurrentUser())) )
    dt = out.return_type
    assert dt.is_record_type
    assert_has_fields(dt, ["me"])

    me = dt.get_child_type("me")
    assert_has_fields(me, ["id", "firstName", "lastName", "birthday", "friends"])

    friends = me.get_child_type("friends")
    assert friends.origin_type == MZTypes.List
    assert_has_fields(friends.type_args[0], ["name"])

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
            ("profilePic", GetProfilePic(id = "$user/id", width = 100, height = 50))
        )
    out = Query().select(
            ("user", d(user = GetUser(id = 4)))
         )
    dt = out.return_type
    assert_has_fields(dt,["user"])
    user = dt.get_child_type("user")
    assert_has_fields(user,["id", "name", "profilePic"])
    ppic = user.get_child_type("profilePic")
    assert ppic == MZTypes.String

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
            ("smallPic", GetProfilePic(id = "$user/id", size = 64)),
            ("bigPic", GetProfilePic(id = "$user/id", size = 1024))
        )
    out = Query().select(
            ("user", d(user = GetUser(id = 4)))
          )
    dt = out.return_type
    assert_has_fields(dt,["user"])
    user = dt.get_child_type("user")
    assert_has_fields(user,["id", "name", "smallPic", "bigPic"])
    ppic = user.get_child_type("smallPic")
    assert ppic == MZTypes.String

def test_no_fragments(mocker):
    """
    https://graphql.github.io/graphql-spec/draft/#example-bcf38
    query noFragments {
      user(id: 4) {
        friends(first: 10) {
          id
          name
          profilePic(size: 50)
        }
        mutualFriends(first: 10) {
          id
          name
          profilePic(size: 50)
        }
      }
    }
    """
    uq = Query().select(
            ("friends", FMap(Query(user = User).select(
                                "id",
                                "name",
                                ("profilePic",
                                    GetProfilePic(id = "$user/id", size = 64))
                            ),
                            GetFriends(id=4, first=10))),
            ("mutualFriends", FMap(Query(user = User).select(
                                "id",
                                "name",
                                ("profilePic",
                                    GetProfilePic(id = "$user/id", size = 64))
                              ), GetMutualFriends(id = 4, first = 10)))
        )
    out = Query().select(("user", uq(_ = GetUser(id = 4))))

    ret_type = out.return_type
    assert_has_fields(ret_type,["user"])
    user = ret_type.get_child_type("user")
    assert_has_fields(user,["friends", "mutualFriends"])

    friends = user.get_child_type("friends").type_args[0]
    mutualFriends = user.get_child_type("mutualFriends").type_args[0]
    assert_has_fields(friends, ["id", "name", "profilePic"])
    assert_has_fields(mutualFriends, ["id", "name", "profilePic"])

def test_with_fragments(mocker):
    """
    https://graphql.github.io/graphql-spec/draft/#example-72b4e
    query withFragments {
      user(id: 4) {
        friends(first: 10) {
          ...friendFields
        }
        mutualFriends(first: 10) {
          ...friendFields
        }
      }
    }

    fragment friendFields on User {
      id
      name
      profilePic(size: 50)
    }
    """
    f1 = Query(user = User).select(
            "id",
            "name",
            ("profilePic", GetProfilePic(id = "$user/id", size = 64))
        )
    uq = Query().select(
            ("friends", # typeof(friends) must be (List/Stream/Scan)[User]
                FMap(f1, GetFriends(id = 4, first = 10))),
            ("mutualFriends", # typeof() must be (List/Stream/Scan)[User]
                FMap(f1, GetMutualFriends(id = 4, first = 10)))
        )
    out = Query().select(("user", uq(_ = GetUser(id = 4))))

    ret_type = out.return_type
    assert_has_fields(ret_type,["user"])
    user = ret_type.get_child_type("user")
    assert_has_fields(user,["friends", "mutualFriends"])

    friends = user.get_child_type("friends").type_args[0]
    mutualFriends = user.get_child_type("mutualFriends").type_args[0]
    assert_has_fields(friends, ["id", "name", "profilePic"])
    assert_has_fields(mutualFriends, ["id", "name", "profilePic"])

def test_nested_fragments(mocker):
    """
        https://graphql.github.io/graphql-spec/draft/#example-fb6c3
        query withNestedFragments {
          user(id: 4) {
            friends(first: 10) {
              ...friendFields
            }
            mutualFriends(first: 10) {
              ...friendFields
            }
          }
        }

        fragment friendFields on User {
          id
          name
          ...standardProfilePic
        }

        fragment standardProfilePic on User {
          profilePic(size: 50)
        }
    """
    f1 = Query(user = User).select(
            ("profilePic", GetProfilePic(id = "$user/id", size = 64)))
    f2 = Query(user = User).select(
            "id",
            "name"
         ).include(f1, user = "$user")
    uq = Query().select(
            ("friends", # typeof(friends) must be (List/Stream/Scan)[User]
                FMap(f2, GetFriends(id = 4, first = 10))),
            ("mutualFriends", # typeof() must be (List/Stream/Scan)[User]
                FMap(f2, GetMutualFriends(id = 4, first = 10)))
        )
    out = Query().select(("user", uq(_ = GetUser(id = 4))))

    ret_type = out.return_type
    assert_has_fields(ret_type,["user"])
    user = ret_type.get_child_type("user")
    assert_has_fields(user,["friends", "mutualFriends"])

    friends = user.get_child_type("friends").type_args[0]
    mutualFriends = user.get_child_type("mutualFriends").type_args[0]
    assert_has_fields(friends, ["id", "name", "profilePic"])
    assert_has_fields(mutualFriends, ["id", "name", "profilePic"])

def test_type_conditions(mocker):
    """
        https://graphql.github.io/graphql-spec/draft/#example-6ce0d
        query FragmentTyping {
            ...userFragment
            ...pageFragment
          }
        }

        fragment userFragment on User {
          friends {
            count
          }
        }

        fragment pageFragment on Page {
          likers {
            count
          }
        }
    """
    uf = Query(user = User).select(
            ("friends", Apply(Query(friends = Friends).select("count"),
                             friends = GetFriends(id = "$user/id"))))
    pf = Query(page = Page).select(
            ("likers", Apply(Query(likers = Likers).select("count"),
                             likers = GetLikers(id = "$page/id"))))
    pq = Query(profile = PageOrUser)        \
            .select("handle")               \
            .include(uf, user = "$profile") \
            .include(pf, page = "$profile")
    out = Query().select(("profiles",
            pq(_ = GetProfiles(handles = ["zuck", "cocacola"]))))

    ret_type = out.return_type
    assert_has_fields(ret_type,["profiles"])
    profiles = ret_type.get_child_type("profiles")
    assert_has_fields(profiles, ["handle", "likers", "friends"])

    friends = profiles.get_child_type("friends")
    likers = profiles.get_child_type("likers")
    assert friends.is_type_app and friends.origin_type == MZTypes.Optional
    assert likers.is_type_app and likers.origin_type == MZTypes.Optional
    assert_has_fields(friends.type_args[0], ["count"])
    assert_has_fields(likers.type_args[0], ["count"])

def test_inline_fragments(mocker):
    """
    https://graphql.github.io/graphql-spec/draft/#example-a6b78
    query inlineFragmentTyping {
      profiles(handles: ["zuck", "cocacola"]) {
        handle
        ... on User {
          friends {
            count
          }
        }
        ... on Page {
          likers {
            count
          }
        }
      }
    }
    """
    pq = Query(profile = PageOrUser)        \
            .select("handle")               \
            .include(Query(user = User).select(
                    ("friends", Apply(Query(friends = Friends).select("count"),
                        friends = GetFriends(id = "$user/id")))),
                    user = "$profile")      \
            .include(Query(page = Page).select(
                        ("likers",
                            Apply(Query(likers = Likers).select("count"),
                                likers = GetLikers(id = "$page/id")))
                    ),
                    page = "$profile")
    out = Query().select(("profiles",
            pq(_ = GetProfiles(handles = ["zuck", "cocacola"]))))
    ret_type = out.return_type
    assert_has_fields(ret_type,["profiles"])
    profiles = ret_type.get_child_type("profiles")
    assert_has_fields(profiles, ["handle", "likers", "friends"])

    friends = profiles.get_child_type("friends")
    likers = profiles.get_child_type("likers")
    assert friends.is_type_app and friends.origin_type == MZTypes.Optional
    assert likers.is_type_app and likers.origin_type == MZTypes.Optional
    assert_has_fields(friends.type_args[0], ["count"])
    assert_has_fields(likers.type_args[0], ["count"])

def test_inline_fragments_optional(mocker):
    """
    https://graphql.github.io/graphql-spec/draft/#example-77377
    query inlineFragmentNoType($expandedInfo: Boolean) {
      user(handle: "zuck") {
        id
        name
        ... @include(if: $expandedInfo) {
          firstName
          lastName
          birthday
        }
      }
    }
    """
    pq = Query(user = User, expandInfo = MZTypes.Bool)          \
            .select(("id", "$user/id"),
                    ("name", "$user/name"))                     \
            .include_if("$expandInfo",
                Query(user = User).select("firstName", "lastName", "birthday"),
                user = "$user")
    out = Query().select(("user", pq(_ = GetUser(handle = "zuck"))))

    ret_type = out.return_type
    assert_has_fields(ret_type,["user"])
    user = ret_type.get_child_type("user")
    assert_has_fields(user, ["id", "name", "firstName", "lastName", "birthday"])
    for fn in ["firstName", "lastName", "birthday"]:
        ftype = user.get_child_type(fn)
        assert ftype.is_type_app and ftype.origin_type == MZTypes.Optional
