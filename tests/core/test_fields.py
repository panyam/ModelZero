
from ipdb import set_trace
from modelzero.core import fields

def test_field_invalid_get(mocker):
    f = fields.Field()
    assert f.__get__(None) == f

def test_field_invalid_set(mocker):
    f = fields.Field()
    try:
        f.__set__(None, "value")
        assert False, "Should have asserted on setter with invalid field_name"
    except AssertionError as ae:
        assert ae.args[0] == "field_name is not set"

    try:
        f.field_name = "test"
        f.__set__(None, "value")
        assert False, "Should have asserted on setter with no instance"
    except AssertionError as ae:
        assert ae.args[0] == "Instance needed for setter"

def test_field_invalid_delete(mocker):
    f = fields.Field()
    try:
        f.__delete__(None)
        assert False, "Should have asserted on deleter with invalid field_name"
    except AssertionError as ae:
        assert ae.args[0] == "field_name is not set"

    try:
        f.field_name = "test"
        f.__delete__(None)
        assert False, "Should have asserted on deleter with no instance"
    except AssertionError as ae:
        assert ae.args[0] == "Instance needed for deleter"

def test_field_set_validate_called(mocker):
    class O:
        __field_values__ = {}
        hello = fields.Field(field_name = "hello")
    instance = O()
    mocker.spy(O.hello, "validate")
    instance.hello = "value"
    O.hello.validate.assert_called_once_with("value")
    assert instance.hello == "value"
    assert getattr(instance, "hello") == "value"

    setattr(instance, "hello", "value2")
    assert instance.hello == "value2"
    assert getattr(instance, "hello") == "value2"
