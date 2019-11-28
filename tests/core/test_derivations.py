
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

def test_derivation_init(mocker):
    d = Query(user = User)
    u = d.get_input("user")
    assert u.is_record_type
    assert u.record_class == UserRecord

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
            ("friends", Bind(Query(friend = User).select("name"),
                             friends = "$user/friends"))
        )
    out = Query().select(
            ("me", Bind(d, user = Func("get_current_user")))
         )
    dt = out.query_type

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
            ("friends", Bind(
                        Query(user = User).select(
                            "id",
                            "name",
                            ("profilePic",
                                Func("get_profile_pic", id = "$user/id", size = 64))
                        ),
                        user__from = Func("get_friends", id = 4, first = 10))),
            ("mutualFriends", Bind(
                        Query(user = User).select(
                            "id",
                            "name",
                            ("profilePic",
                                Func("get_profile_pic", id = "$user/id", size = 64))
                        ), 
                        user__from = Func("get_mutual_friends", id = 4, first = 10)))
        )
    out = Query().select(("user", Bind(uq, _ = Func("get_user", id = 4))))

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
            ("profilePic", Func("get_profile_pic", id = "$user/id", size = 64))
        )
    uq = Query().select(
            ("friends", # typeof(friends) must be (List/Stream/Scan)[User]
                FMap(f1, user__from = Func("get_friends", id = 4, first = 10))),
            ("mutualFriends", # typeof() must be (List/Stream/Scan)[User]
                Bind(f1, user__from = Func("get_mutual_friends", id = 4, first = 10)))
        )
    out = Query().select(("user", Bind(uq, _ = Func("get_user", id = 4))))


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
            ("profilePic", Func("get_profile_pic", id = "$user/id", size = 64)))
    f2 = Query(user = User).select(
            "id",
            "name"
         ).include(f1, user = "$user")
    uq = Query().select(
            ("friends", # typeof(friends) must be (List/Stream/Scan)[User]
                FMap(f2, user__from = Func("get_friends", id = 4, first = 10))),
            ("mutualFriends", # typeof() must be (List/Stream/Scan)[User]
                Bind(f2, user__from = Func("get_mutual_friends", id = 4, first = 10)))
        )
    out = Query().select(("user", Bind(uq, _ = Func("get_user", id = 4))))

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
            ("friends", Bind(Query(friends = Friends).select("count"),
                             friends = Func("get_friends", id = "$user/id"))))
    pf = Query(page = Page).select(
            ("likers", Bind(Query(likers = Likers).select("count"),
                             likers = Func("get_likers", id = "$page/id"))))
    pq = Query(profile = PageOrUser)        \
            .select("handle")               \
            .include(uf, user = "$profile") \
            .include(pf, page = "$profile")
    out = Query().select(("profiles",
            Bind(pq, _ = Func("get_profiles", handles = ["zuck", "cocacola"]))))


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
                    ("friends", Bind(Query(friends = Friends).select("count"),
                        friends = Func("get_friends", id = "$user/id")))),
                    user = "$profile")      \
            .include(Query(page = Page).select(
                        ("likers",
                            Bind(Query(likers = Likers).select("count"),
                                likers = Func("get_likers", id = "$page/id")))
                    ),
                    page = "$profile")
    out = Query().select(("profiles",
            Bind(pq, _ = Func("get_profiles", handles = ["zuck", "cocacola"]))))

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
            Bind(pq, _ = Func("get_user", handle = "zuck"))))
