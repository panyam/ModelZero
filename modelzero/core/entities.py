
from typing import List
from modelzero.core.records import *

KEY_FIELD = "__key__"

# TODO _ Should this be a Model instance?
# Advantage of this would be we have more typing and a stronger relationship 
# between the entity fields this Key is referring to.
class Key(object):
    """ Generic Key objects that encapsulate how keys for entities are stored and used. """
    def __init__(self, entity_class, *parts):
        self.entity_class = entity_class
        self.fromValue(*parts)

    def to_json(self):
        return self.value

    @property
    def size(self):
        return len(self.parts)

    @property
    def has_id(self):
        return len(self.parts) > 0

    @property
    def first_part(self):
        return self.parts[0]

    @property
    def value(self):
        if self.size == 1:
            return self.parts[0]
        else:
            return "/".join(map(str, self.parts))

    def fromValue(self, *id_or_value):
        if len(id_or_value) == 1:
            id_or_value = id_or_value[0]
        T = type(id_or_value)
        if T is int:
            parts = [id_or_value]
        elif T in (list, tuple):
            parts = id_or_value
        elif T is str:
            parts = id_or_value.split("/")
        else:
            set_trace()
            assert False, "id_or_value must be str, int, list or tuple"
        kf = self.entity_class.key_fields()
        self.parts = []
        if not kf:
            if len(parts) != 1:
                set_trace()
                assert False
            self.parts = parts
        else:
            if len(parts) != len(kf):
                set_trace()
            assert len(parts) == len(kf), "Number of parts in key is not same as number of key fields"
            for f,v in zip(kf, parts):
                # Validate field 
                value = self.entity_class.__record_fields__[f].validate(v)
                self.parts.append(value)

    def __eq__(self, another):
        if another is None or type(another) is not Key: return False
        return self.entity_class == another.entity_class and self.parts == another.parts

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(str(self))

    @property
    def uri(self):
        return self.entity_class.__name__.lower() + ":" + str(self)

class Entity(Record):
    def __init__(self, **kwargs):
        setattr(self, KEY_FIELD, None)
        super(Entity, self).__init__(**kwargs)

    @classmethod
    def Key(cls, *parts):
        return Key(cls, *parts)

    @classmethod
    def key_fields(cls) -> List[str]:
        """ The key for an entity can either be an auto-assigned one 
        or a composite key based on other fields. """
        return None

    def is_key_field(self, k : str) -> bool:
        """ Returns True if a given field name 'k' is a key field. """
        if k == KEY_FIELD: return True
        kf = self.key_fields()
        if kf and len(kf) == 1 and kf[0] == k: return True
        return False

    def getkey(self) -> Key:
        """ Return the ID of this entity. """
        kf = self.key_fields()
        if kf:
            # if any of the key fields is None, then our key is None
            keyvals = [getattr(self, f) for f in kf]
            for kv in keyvals:
                if kv is None:
                    return None
            return Key(self.__class__, *keyvals)
        else:
            if getattr(self, KEY_FIELD) is None: return None
            return Key(self.__class__, getattr(self, KEY_FIELD))

    def setkey(self, key : Key):
        """ Set's the value of the key for this entity.  This will result in the change of the entity itself being represented in the table. """
        if type(key) is not Key:
            key = Key(self.__class__, key)
        kf = self.key_fields()
        if not kf:
            assert key.size == 1, "Number of parts of key of default type must be 1"
            setattr(self, KEY_FIELD, key.first_part)
        else:
            assert len(kf) == key.size, "Number of parts in key is not same as number of key fields"
            for f,v in zip(kf, key.parts):
                self.setfield(f, v)

    def __contains__(self, fieldname):
        if fieldname == KEY_FIELD and self.getkey() != None:
            return True
        return super().__contains__(fieldname)

    def __getitem__(self, fieldname):
        if fieldname == KEY_FIELD:
            return self.getkey()
        return super().__getitem__(fieldname)

    def setfield(self, fieldname, value, reject_invalid_field = False):
        if fieldname == KEY_FIELD:
            self.setkey(value)
        else:
            super().setfield(fieldname, value, reject_invalid_field)
        return self


