
from ipdb import set_trace
import datetime
import typing
from typing import TypeVar, Generic
import datetime
from . import errors

class Field(object):
    USE_DEFAULT = None
    def __init__(self, **kwargs):
        self.field_name = kwargs.get("field_name", None)
        self.checker_name = kwargs.get("checker_name",
                                        None if not self.field_name
                                             else "has_" + self.field_name)
        self.default_value = kwargs.get("default", None)
        self.validators = kwargs.get("validators", [])
        self.required = kwargs.get("required", True)

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

class LeafField(Field):
    """ Leaf fields are simple fields that are stored as a single logical field. """
    def __init__(self, base_type = None, **kwargs):
        Field.__init__(self, **kwargs)
        self.base_type = base_type

    @property
    def logical_type(self):
        if not self.base_type:
            raise Exception("basetype not found")
        return self.base_type

    def validate(self, value):
        if self.base_type:
            if not isinstance(value, self.base_type):
                value = self.base_type(value)
        return super().validate(value)
