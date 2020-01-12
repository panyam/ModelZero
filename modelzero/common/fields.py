
from ipdb import set_trace
from modelzero.core import types
from modelzero.core.types import MZTypes
from modelzero.core.records import *
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn

def ListField(child_type, **kwargs):
    return Field(MZTypes.List[child_type], **kwargs)

def MapField(key_type, value_type, **kwargs):
    mt = MZTypes.Map[key_type, value_type]
    return Field(mt, **kwargs)

# from typing import TypeVar, Generic
def KeyField(entity_class, **kwargs):
    return Field(MZTypes.Key[entity_class], **kwargs)

class DateTimeField(Field):
    def __init__(self, **kwargs):
        Field.__init__(self, MZTypes.DateTime, **kwargs)

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
