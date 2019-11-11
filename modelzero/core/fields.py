
from ipdb import set_trace
import datetime
import datetime
from . import errors
from . import types

IntType = types.Type.as_opaque_type("int", int)
LongType = types.Type.as_opaque_type("long", int)
StrType = types.Type.as_opaque_type("str", str)
BytesType = types.Type.as_opaque_type("bytes", bytes)
URLType = types.Type.as_opaque_type("URL", str)
BoolType = types.Type.as_opaque_type("bool", bool)
FloatType = types.Type.as_opaque_type("float", float)
DoubleType = types.Type.as_opaque_type("double", float)
ListType = types.Type.as_opaque_type("list", list)
MapType = types.Type.as_opaque_type("map", map)
KeyType = types.Type.as_opaque_type("key")
DateTimeType = types.Type.as_opaque_type("DateTime", datetime.datetime)
OptionalType = types.Type.as_opaque_type("Optional")

class Field(object):
    USE_DEFAULT = None
    def __init__(self, **kwargs):
        self.field_name = kwargs.get("field_name", None)
        self.checker_name = kwargs.get("checker_name",
                                        None if not self.field_name
                                             else "has_" + self.field_name)
        self.default_value = kwargs.get("default", None)
        self.validators = kwargs.get("validators", [])
        self.optional = kwargs.get("optional", False)

    def __get__(self, instance, objtype = None):
        if instance is None:
            return self
        assert self.field_name is not None, "field_name is not set"
        assert instance is not None, "Instance needed for getter"
        return instance.__field_values__.get(self.field_name, self.default_value)

    def __delete__(self, instance):
        assert self.field_name is not None, "field_name is not set"
        assert instance is not None, "Instance needed for deleter"
        if self.field_name in instance.__field_values__:
            del instance.__field_values__[self.field_name]

    def __set__(self, instance, value):
        assert self.field_name is not None, "field_name is not set"
        assert instance is not None, "Instance needed for setter"
        value = self.validate(value)
        instance.__field_values__[self.field_name] = value

    def validate(self, value):
        for validator in self.validators:
            value = validator(value)
        return value

    def makechecker(self, field_name):
        return property(lambda x: field_name in x.__field_values__)

    def makeproperty(self, field_name):
        def getter(instance):
            return instance.__field_values__.get(field_name, self.default_value)
        def setter(instance, value):
            instance.__field_values__[field_name] = value
        return property(getter, setter)

    def wrap_optionality(self, thetype):
        if self.optional:
            thetype = OptionalType[thetype]
        return thetype

class LeafField(Field):
    """ Leaf fields are simple fields that are stored as a single logical field. """
    def __init__(self, base_type = None, **kwargs):
        Field.__init__(self, **kwargs)
        if base_type:
            from modelzero.core import types
            if type(base_type) is not types.Type:
                set_trace()
        self.base_type = base_type

    @property
    def logical_type(self):
        if not self.base_type:
            raise Exception("basetype not found")
        return self.wrap_optionality(self.base_type)

    def validate(self, value):
        if self.base_type:
            if not isinstance(value, self.base_type):
                value = self.base_type(value)
        return super().validate(value)
