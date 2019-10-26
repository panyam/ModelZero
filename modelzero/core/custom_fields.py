
from ipdb import set_trace
from modelzero.core.fields import *
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn

K = TypeVar("K", str, Entity)

class URL(str): pass

class KeyType(Generic[K]): pass   

class KeyField(LeafField):
    def __init__(self, entity_class, **kwargs):
        LeafField.__init__(self, KeyType[entity_class], **kwargs)

    @property
    def key_type(self):
        return self.base_type

    @property
    def entity_class(self):
        set_trace()
        return self.key_type.entity_class

    def validate(self, value):
        self.key_type.resolve()
        from modelzero.core.entities import Key
        if type(value) is not Key:
            value = self.entity_class.Key(value)
        assert value.entity_class == self.entity_class, "Entity classes of key field ({}) and key value ({}) do not match".format(self.entity_class, value.entity_class)
        return super().validate(value)

class ListField(Field):
    def __init__(self, child_type, **kwargs):
        Field.__init__(self, **kwargs)
        self.child_type = child_type
        self._logical_type = typing.List[child_type]

    @property
    def logical_type(self):
        return self._logical_type

class StructField(Field):
    def __init__(self, model_class, **kwargs):
        Field.__init__(self, **kwargs)
        self.model_class = model_class

class MapField(Field):
    def __init__(self, key_type, value_type, **kwargs):
        Field.__init__(self, **kwargs)
        self.key_type = key_type
        self.value_type = value_type
        self._logical_type = typing.Dict[key_type, value_type]

    @property
    def logical_type(self):
        return self._logical_type

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
                value = datetime.datetime.strptime(value, "%Y-%m-%d %h:%m:%s")
        elif type(value) is int:
            value = datetime.datetime.utcfromtimeoffset(value)
        else:
            value = value.replace(tzinfo = None)
        return super().validate(value)

class JsonField(LeafField): pass
class FractionField(LeafField): pass
