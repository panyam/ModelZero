
from ipdb import set_trace
from modelzero.core.derivations import Query, Apply, FMap
from modelzero.core.types import Type
from modelzero.core.custom_types import MZTypes
from modelzero.core.records import *
from modelzero.core import custom_fields as fields

class Date(Record):
    day = fields.Field(MZTypes.Int)
    month = fields.Field(MZTypes.Int)
    year = fields.Field(MZTypes.Int)

class UserRecord(Record):
    id = fields.Field(MZTypes.String)
    firstName = fields.Field(MZTypes.String)
    lastName = fields.Field(MZTypes.String)
    name = fields.Field(MZTypes.String)
    created_at = fields.DateTimeField()
    birthday = fields.Field(Type.as_record_type(Date))
    friends = fields.ListField("User")
User = Type.as_record_type(UserRecord)

class PageRecord(Record):
    id = fields.Field(MZTypes.String)
    url = fields.Field(MZTypes.URL)
Page = Type.as_record_type(PageRecord)

PageOrUser = Type.as_sum_type(Page, User)

class FriendsRecord(Record):
    count = fields.Field(MZTypes.Int)
Friends = Type.as_record_type(FriendsRecord)

class LikersRecord(Record):
    count = fields.Field(MZTypes.Int)
Likers = Type.as_record_type(LikersRecord)

def get_user(id : int) -> User:
    pass

def get_current_user() -> User:
    pass

def get_profile_pic(id : int, size : int = 100, width : int = 100, height : int = 100) -> str:
    pass

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
            ("birthday", Apply(Query(date = Date).select("month", "day"),
                              date = "$user/birthday")),
            ("friends", FMap(Query(friend = User).select("name"), 
                             friend__from = "$user/friends"))
        )
    out = Query().select(
            ("me", Apply(d, user = Apply(get_current_user)))
         )
    dt = out.return_type
    assert dt.is_record_type
    rmeta = dt.record_class.__record_metadata__
    assert rmeta.num_fields == 1

    assert "me" in rmeta
    me = rmeta["me"].logical_type
    assert me.is_record_type
    rmeta = me.record_class.__record_metadata__
    assert rmeta.num_fields == 5
    assert "id" in rmeta
    assert "firstName" in rmeta
    assert "lastName" in rmeta
    assert "birthday" in rmeta
    friends = rmeta["friends"]
    friends_type = friends.logical_type
    assert friends_type.is_type_app
    set_trace()

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
            ("profilePic", Apply(get_profile_pic, id = "$user/id", width = 100, height = 50))
        )
    out = Query().select(
            ("user", d(user = Apply(get_user, id = 4)))
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
            ("smallPic", Apply(get_profile_pic, id = "$user/id", size = 64)),
            ("bigPic", Apply(get_profile_pic, id = "$user/id", size = 1024))
        )
    out = Query().select(
            ("user", d(user = Apply(get_user, id = 4)))
         )


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
                                    Apply(get_profile_pic,
                                            id = "$user/id", size = 64))
                            ),
                            user__from = Apply(get_friends, id=4, first=10))),
            ("mutualFriends", FMap(Query(user = User).select(
                                "id",
                                "name",
                                ("profilePic",
                                    Apply(get_profile_pic,
                                        id = "$user/id", size = 64))
                            ), 
                            user__from = Apply(get_mutual_friends,
                                            id = 4, first = 10)))
        )
    out = Query().select(("user", Apply(uq, _ = Apply(get_user, id = 4))))

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
            ("profilePic", Apply(get_profile_pic, id = "$user/id", size = 64))
        )
    uq = Query().select(
            ("friends", # typeof(friends) must be (List/Stream/Scan)[User]
                FMap(f1, user__from = Apply(get_friends, id = 4, first = 10))),
            ("mutualFriends", # typeof() must be (List/Stream/Scan)[User]
                FMap(f1, user__from = Apply(get_mutual_friends, id = 4, first = 10)))
        )
    out = Query().select(("user", Apply(uq, _ = Apply(get_user, id = 4))))


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
            ("profilePic", Apply(get_profile_pic, id = "$user/id", size = 64)))
    f2 = Query(user = User).select(
            "id",
            "name"
         ).include(f1, user = "$user")
    uq = Query().select(
            ("friends", # typeof(friends) must be (List/Stream/Scan)[User]
                FMap(f2, user__from = Apply(get_friends, id = 4, first = 10))),
            ("mutualFriends", # typeof() must be (List/Stream/Scan)[User]
                FMap(f2, user__from = Apply(get_mutual_friends, id = 4, first = 10)))
        )
    out = Query().select(("user", Apply(uq, _ = Apply(get_user, id = 4))))

def test_type_conditions(mocker):
    """
        https://graphql.github.io/graphql-spec/draft/#example-6ce0d
        query FragmentTyping {
          profiles(handles: ["zuck", "cocacola"]) {
            handle
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
                             friends = Apply(get_friends, id = "$user/id"))))
    pf = Query(page = Page).select(
            ("likers", Apply(Query(likers = Likers).select("count"),
                             likers = Apply(get_likers, id = "$page/id"))))
    pq = Query(profile = PageOrUser)        \
            .select("handle")               \
            .include(uf, user = "$profile") \
            .include(pf, page = "$profile")
    out = Query().select(("profiles",
            Apply(pq, _ = Apply(get_profiles, handles = ["zuck", "cocacola"]))))


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
                        friends = Apply(get_friends, id = "$user/id")))),
                    user = "$profile")      \
            .include(Query(page = Page).select(
                        ("likers",
                            Apply(Query(likers = Likers).select("count"),
                                likers = Apply(get_likers, id = "$page/id")))
                    ),
                    page = "$profile")
    out = Query().select(("profiles",
            Apply(pq, _ = Apply(get_profiles, handles = ["zuck", "cocacola"]))))

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
            .select("id", "name")                               \
            .include_if("$expandInfo",
                Query(user = User).select("firstName", "lastName", "birthday"),
                user = "$user")
    out = Query().select(("user",
            Apply(pq, _ = Apply(get_user, handle = "zuck"))))
