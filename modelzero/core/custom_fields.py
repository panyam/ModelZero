
from ipdb import set_trace
from modelzero.core.fields import *
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn
from typing import TypeVar, Generic, List, Dict

K = TypeVar("K", str, Entity)

class ListField(Field):
    def __init__(self, child_type, **kwargs):
        Field.__init__(self, **kwargs)
        self.child_type = child_type
        self._logical_type = List[child_type]

    @property
    def logical_type(self):
        return self._logical_type

class MapField(Field):
    def __init__(self, key_type, value_type, **kwargs):
        Field.__init__(self, **kwargs)
        self.key_type = key_type
        self.value_type = value_type
        self._logical_type = Dict[key_type, value_type]

    @property
    def logical_type(self):
        return self._logical_type

class NativeField(Field):
    def __init__(self, wrapped_type, **kwargs):
        Field.__init__(self, **kwargs)
        self._logical_type = wrapped_type

    @property
    def logical_type(self):
        return self._logical_type

class URL(str): pass

class KeyType(Generic[K]):
    def __call__(self, *args, **kwargs):
        set_trace()

class KeyField(LeafField):
    def __init__(self, entity_class, **kwargs):
        LeafField.__init__(self, KeyType[entity_class], **kwargs)
        self._entity_class = entity_class

    @property
    def entity_class(self):
        if type(self._entity_class) is str:
            resolved, self._entity_class = resolve_fqn(self._entity_class)
            assert resolved, f"Could not resolve entity class: {self._entity_class}"
        return self._entity_class

    def validate(self, value):
        from modelzero.core.entities import Key
        if type(value) is not Key:
            value = self.entity_class.Key(value)
        assert value.entity_class == self.entity_class, "Entity classes of key field ({}) and key value ({}) do not match".format(self.entity_class, value.entity_class)
        return value
        # return super().validate(value)

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

class URLField(LeafField):
    def __init__(self, **kwargs):
        LeafField.__init__(self, URL, **kwargs)

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
                value = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        elif type(value) is int:
            value = datetime.datetime.utcfromtimeoffset(value)
        else:
            value = value.replace(tzinfo = None)
        return super().validate(value)

class JsonField(LeafField): pass

