
import importlib
from ipdb import set_trace
import datetime
import typing
from typing import TypeVar, Generic
import datetime
from . import errors

def resolve_fqn(fqn):
    resolved = type(fqn) is not str
    if not resolved:
        parts = fqn.split(".")
        first,last = parts[:-1],parts[-1]
        module = ".".join(first)
        module = importlib.import_module(module)
        result = getattr(module, last)
        resolved = True
    return resolved, result

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
    def __init__(self, key_type, value_type, **kwargs):
        Field.__init__(self, **kwargs)
        self.key_type = key_type
        self.value_type = value_type
        self.key_resolved = type(key_type) is not str
        self.value_resolved = type(value_type) is not str

    def resolve(self):
        if not self.key_resolved:
            self.key_resolved, self.key_type = resolve_fqn(self.key_type)
        if not self.value_resolved:
            self.value_resolved, self.value_type = resolve_fqn(self.value_type)
        return self.key_resolved and self.value_resolved

class ListField(Field):
    def __init__(self, child_type, **kwargs):
        Field.__init__(self, **kwargs)
        self.resolved = type(child_type) is not str
        self.child_type = child_type

    def resolve(self):
        if not self.resolved:
            self.resolved, self.child_type = resolve_fqn(self.child_type)
        return self.resolved

class LeafField(Field):
    """ Leaf fields are simple fields that are stored as a single logical field. """
    def __init__(self, base_type = None, **kwargs):
        Field.__init__(self, **kwargs)
        self.base_type = base_type

    def validate(self, value):
        if self.base_type:
            if not isinstance(value, self.base_type):
                value = self.base_type(value)
        return super().validate(value)

class RefField(LeafField):
    def __init__(self, model_class, **kwargs):
        Field.__init__(self, **kwargs)
        self.model_class = model_class

class BytesField(LeafField):
    def __init__(self, **kwargs):
        LeafField.__init__(self, bytes, **kwargs)

class StringField(LeafField):
    def __init__(self, **kwargs):
        LeafField.__init__(self, str, **kwargs)

class IntegerField(LeafField):
    def __init__(self, **kwargs):
        LeafField.__init__(self, int, **kwargs)

class LongField(LeafField):
    def __init__(self, **kwargs):
        LeafField.__init__(self, int, **kwargs)

class BooleanField(LeafField):
    def __init__(self, **kwargs):
        LeafField.__init__(self, bool, **kwargs)

class FloatField(LeafField):
    def __init__(self, **kwargs):
        LeafField.__init__(self, float, **kwargs)

class DateTimeField(LeafField):
    def __init__(self, **kwargs):
        LeafField.__init__(self, datetime.datetime, **kwargs)

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

class URLField(LeafField): pass
class JsonField(LeafField): pass
class FractionField(LeafField): pass
class AnyField(LeafField): pass

class KeyField(LeafField):
    def __init__(self, entity_class, **kwargs):
        LeafField.__init__(self, **kwargs)
        self.resolved = type(entity_class) is not str
        self.entity_class = entity_class

    def resolve(self):
        if not self.resolved:
            self.resolved, self.entity_class = resolve_fqn(self.entity_class)
        return self.resolved

    def validate(self, value):
        assert self.resolve(), f"Could not resolve entity: {self.entity_class}"
        from modelzero.core.entities import Key
        if type(value) is not Key:
            value = self.entity_class.Key(value)
        assert value.entity_class == self.entity_class, "Entity classes of key field ({}) and key value ({}) do not match".format(self.entity_class, value.entity_class)
        return super().validate(value)
