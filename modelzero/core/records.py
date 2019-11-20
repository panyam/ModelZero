
from collections import defaultdict
from taggedunion import Union, Variant
from ipdb import set_trace
import typing
from modelzero.utils import with_metaclass
from modelzero.core import errors

class Field(object):
    USE_DEFAULT = None
    def __init__(self, base_type = None, **kwargs):
        self.field_name = kwargs.get("field_name", None)
        self.checker_name = kwargs.get("checker_name",
                                        None if not self.field_name
                                             else "has_" + self.field_name)
        self._default = kwargs.get("default", None)
        self.validators = kwargs.get("validators", [])
        self.optional = kwargs.get("optional", False)
        self.base_type = base_type

    @property
    def base_type(self):
        return self._base_type

    @base_type.setter
    def base_type(self, newtype):
        if newtype:
            from modelzero.core import types
            if type(newtype) is not types.Type:
                set_trace()
        self._base_type = newtype

    @property
    def default_value(self):
        if self._default is None: return None
        if hasattr(self._default, "__call__"): return self._default()
        return self._default

    def clone(self):
        kwargs = { }
        if self.field_name: kwargs["field_name"] = self.field_name
        if self.checker_name: kwargs["checker_name"] = self.checker_name
        if self._default : kwargs["default"] = self._default
        if self.validators: kwargs["validators"] = self.validators
        if self.optional: kwargs["optional"] = self.optional
        return Field(self.base_type, **kwargs)

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
        if self.base_type and self.base_type.is_opaque_type and self.base_type.native_type:
            if not isinstance(value, self.base_type.native_type):
                value = self.base_type.native_type(value)
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
            from modelzero.core.custom_types import MZTypes
            thetype = MZTypes.Optional[thetype]
        return thetype

    @property
    def logical_type(self):
        if not self.base_type:
            raise Exception("basetype not found")
        return self.wrap_optionality(self.base_type)

class RecordBase(object):
    """ Records are our base of all objects that need a representation. """
    def __init__(self, **kwargs):
        self.__field_values__ = {}
        self.apply_patch(kwargs, reject_invalid_fields = True)

    @classmethod
    def register_field(cls, fieldname : str, field : "Type"):
        field.field_name = fieldname

        # What do we do if the field is already present 
        # (ie via a base class or via a duplicate declaration)?
        cls.__record_fields__[fieldname] = field
        # if not field.checker_name: field.checker_name = "has_" + fieldname
        # setattr(cls, field.checker_name, field.makechecker(fieldname))

    def __repr__(self):
        return "<%s.%s at %x>" % (self.__class__.__module__, self.__class__.__name__, id(self))

    def __eq__(self, another):
        if another is None: return False
        if type(self) != type(another): return False
        # Compare all fields
        for k in self.__record_fields__:
            if getattr(self, k) != getattr(another, k):
                return False
        return True

    def __contains__(self, fieldname):
        if fieldname.startswith("has_"): set_trace()
        return fieldname in self.__field_values__

    def __getitem__(self, fieldname):
        if fieldname not in self.__record_fields__:
            raise Exception(f"Invalid field name: {fieldname}")
        return getattr(self, fieldname)

    def get(self, fieldname, on_missing = None):
        return self.__getitem__(fieldname)

    def setfield(self, fieldname, value, reject_invalid_field = False):
        if fieldname not in self.__record_fields__:
            if reject_invalid_field: 
                set_trace()
                raise Exception(f"Invalid field name: '{fieldname}'")
        else:
            setattr(self, fieldname, value)
        return self

    def apply_patch(self, patch, reject_invalid_fields = False):
        for fieldname, value in patch.items():
            self.setfield(fieldname, value, reject_invalid_fields)
        return self

    def validate(self):
        field_errors = defaultdict(list)
        for name, field in self.__record_fields__.items():
            ftype = field.logical_type
            fvalue = self.__field_values__.get(name, field.default_value)
            # TODO - should optional and nullable be treated differently?
            if fvalue is None:
                if not field.optional:
                    field_errors[name].append(errors.ValidationError(f"Required field {name} has no value"))
                    continue
            # Validate value
            field.validate(fvalue)
        if field_errors:
            set_trace()
            raise errors.ValidationError(f"Validation failed for {self.__class__}", field_errors)
        return self

class RecordMeta(type):
    def __new__(cls, name, bases, dct):
        x = super().__new__(cls, name, bases, dct)

        # Evaluate FQN
        x.__fqn__ = dct.get("__fqn__", ".".join([x.__module__, name]))

        # Register all fields
        __record_fields__ = getattr(x, "__record_fields__", {}).copy()
        setattr(x, "__record_fields__", __record_fields__)
        for fieldname,entry in x.__dict__.copy().items():
            if issubclass(entry.__class__, Field):
                x.register_field(fieldname, entry)
        return x

class Record(with_metaclass(RecordMeta, RecordBase)):
    pass

class PatchRecordBase(Record):
    """ Patch objects represent the "patch actions" that can be performed on the fields of a Record. """
    pass

class PatchRecordMeta(RecordMeta):
    def __new__(cls, name, bases, dct):
        x = super().__new__(cls, name, bases, dct)
        record_class = getattr(x, "RecordClass", None)
        if False and not record_class and (len(bases) != 1 or bases[0] != PatchRecordBase):
            set_trace()
            raise Exception("PatchRecord class MUST have an RecordClass class attribute to indicate resource classes being patched.")
        return x

class PatchRecord(with_metaclass(PatchRecordMeta, PatchRecordBase)):
    pass

PT = typing.TypeVar("PT")
ET = typing.TypeVar("ET")
KT = typing.TypeVar("KT")
class PatchDoc(typing.Generic[ET]): pass
class Patch(typing.Generic[KT, ET, PT]): pass

class PatchCommand(Union, typing.Generic[PT]):
    SET = Variant(PT)
    DELETE = Variant(None)  # No associated type

class ListPatchCommand(Union, typing.Generic[ET, PT]):
    SET = Variant(typing.List[ET])
    DELETE = Variant(None)
    REPLACE = Variant(typing.Tuple[int, PT])
    INSERT = Variant(typing.Tuple[int, PT])
    REMOVE = Variant(typing.List[int])
    SWAP = Variant(typing.Tuple[int, int])
