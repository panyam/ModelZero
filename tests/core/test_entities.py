
from ipdb import set_trace
from modelzero.core import fields, entities

def test_entity_create(mocker):
    class E(entities.Entity):
        f1 = fields.StringField()
        f2 = fields.IntegerField()
        f3 = fields.FloatField()
        f4 = fields.BooleanField()

    assert len(E.__model_fields__) == 4
    assert hasattr(E, "has_f1")
    assert hasattr(E, "has_f2")
    assert hasattr(E, "has_f3")
    assert hasattr(E, "has_f4")

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
        f1 = fields.StringField()
        f2 = fields.IntegerField()
        f3 = fields.FloatField()
        f4 = fields.BooleanField()

        @classmethod
        def key_fields(cls):
            return ["f1", "f2"]

    e = E2(f1 = "hello", f2 = 42)
    assert e.getkey() == E2.Key("hello/42")
