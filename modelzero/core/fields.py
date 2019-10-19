
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

class StructField(Field):
    def __init__(self, model_class, **kwargs):
        Field.__init__(self, **kwargs)
        self.model_class = model_class

class MapField(Field):
    def __init__(self, key_class, value_class, **kwargs):
        Field.__init__(self, **kwargs)
        self.key_class = key_class
        self.value_class = value_class

class ListField(Field):
    def __init__(self, child_class, **kwargs):
        Field.__init__(self, **kwargs)
        self.child_class = child_class

class LeafField(Field):
    """ Leaf fields are simple fields that are stored as a single logical field. """
    pass

class KeyField(LeafField):
    def __init__(self, entity_class, **kwargs):
        Field.__init__(self, **kwargs)
        self.resolved = type(entity_class) is not str
        self.entity_class = entity_class

    def validate(self, value):
        if not self.resolved:
            parts = self.entity_class.split(".")
            first,rest,last = parts[0],parts[1:-1],parts[-1]
            curr = head = __import__(first)
            for part in rest:
                curr = getattr(curr, part)
            self.entity_class = getattr(curr, last)
            self.resolved = type(self.entity_class) is not str
        from modelzero.core.entities import Key
        if type(value) is not Key:
            value = self.entity_class.Key(value)
        assert value.entity_class == self.entity_class, "Entity classes of key field ({}) and key value ({}) do not match".format(self.entity_class, value.entity_class)
        return super().validate(value)

class RefField(LeafField):
    def __init__(self, model_class, **kwargs):
        Field.__init__(self, **kwargs)
        self.model_class = model_class

class BytesField(LeafField):
    def validate(self, value):
        value = bytes(value)
        return super().validate(value)

class StringField(LeafField):
    def validate(self, value):
        value = str(value)
        return super().validate(value)

class IntegerField(LeafField):
    def validate(self, value):
        value = int(value)
        return super().validate(value)

class LongField(LeafField):
    def validate(self, value):
        value = int(value)
        return super().validate(value)

class BooleanField(LeafField):
    def validate(self, value):
        value = int(value)
        return super().validate(value)

class FloatField(LeafField):
    def validate(self, value):
        value = float(value)
        return super().validate(value)

class DateTimeField(LeafField):
    def validate(self, value):
        if type(value) is str:
            try:
                value = datetime.datetime.strptime(value, "%Y-%m-%d")
            except:
                value = datetime.datetime.strptime(value, "%Y-%m-%d %h:%m:%s")
        elif type(value) is int:
            value = datetime.datetime.utcfromtimeoffset(value)
        else:
            value = value.replace(tzinfo = None)
        return super().validate(value)

class URIField(LeafField): pass
class JsonField(LeafField): pass
class FractionField(LeafField): pass
class AnyField(LeafField): pass
