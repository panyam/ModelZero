
from ipdb import set_trace
from modelzero.core.derivations import Derivation
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
    d = Derivation("MyDerivation", user = User)
    u = d.get_input("user")
    assert u.is_record_type
    assert u.record_class == User

    dt = d.derived_type
    rc = dt.record_class
    assert dt.is_record_type
    assert rc

    # Ensure it has exactly the fields needed
    set_trace()
    assert dt.fields
