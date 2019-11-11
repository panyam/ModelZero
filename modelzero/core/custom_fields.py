
from ipdb import set_trace
from modelzero.core import types
from modelzero.core.fields import *
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn

class ListField(Field):
    def __init__(self, child_type, **kwargs):
        Field.__init__(self, **kwargs)
        self.child_type = child_type
        # self._logical_type = List[child_type]
        self._logical_type = ListType[child_type]

    @property
    def logical_type(self):
        return self.wrap_optionality(self._logical_type)

class MapField(Field):
    def __init__(self, key_type, value_type, **kwargs):
        Field.__init__(self, **kwargs)
        self.key_type = key_type
        self.value_type = value_type
        self._logical_type = MapType[key_type, value_type]

    @property
    def logical_type(self):
        return self.wrap_optionality(self._logical_type)

# from typing import TypeVar, Generic

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
        set_trace()
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

class DateTimeField(LeafField):
    def __init__(self, **kwargs):
        LeafField.__init__(self, DateTimeType, **kwargs)

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

