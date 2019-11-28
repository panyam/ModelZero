
from ipdb import set_trace
from modelzero.core import entities
from modelzero.core import custom_fields as fields
from modelzero.core import custom_types as types

def test_entity_create(mocker):
    class E(entities.Entity):
        f1 = fields.Field(types.MZTypes.String)
        f2 = fields.Field(types.MZTypes.Int)
        f3 = fields.Field(types.MZTypes.Float)
        f4 = fields.Field(types.MZTypes.Bool)

    assert len(E.__record_fields__) == 4

    e = E(f1 = 0, f2 = 3, f3 = "5.5", f4 = True)
    assert e.f1 == "0"
    assert e.f2 == 3
    assert e.f3 == 5.5
    assert e.f4 == True

    e1 = E(f1 = 0, f2 = 3, f3 = "5.5", f4 = True)
    e2 = E(f1 = 0, f2 = 3, f3 = "5.5", f4 = True)
    assert e1 == e2

def test_entity_keyfields(mocker):
    class E2(entities.Entity):
        f1 = fields.Field(types.MZTypes.String)
        f2 = fields.Field(types.MZTypes.Int)
        f3 = fields.Field(types.MZTypes.Float)
        f4 = fields.Field(types.MZTypes.Bool)

        @classmethod
        def key_fields(cls):
            return ["f1", "f2"]

    e = E2(f1 = "hello", f2 = 42)
    assert e.getkey() == E2.Key("hello/42")
