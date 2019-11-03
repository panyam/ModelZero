
from ipdb import set_trace
import datetime
import typing
from taggedunion import Union, Variant
from typing import TypeVar, Generic, List, Tuple
import datetime
from modelzero.core.fields import Field
from modelzero.utils import with_metaclass

class ModelBase(object):
    """ Models are our base of all objects that need a representation. """
    def __init__(self, **kwargs):
        self.__field_values__ = {}
        self._validators = []
        self.apply_patch(kwargs, reject_invalid_fields = True)

    @classmethod
    def register_field(cls, fieldname : str, field : Field):
        field.field_name = fieldname

        # What do we do if the field is already present 
        # (ie via a base class or via a duplicate declaration)?
        cls.__model_fields__[fieldname] = field
        # if not field.checker_name: field.checker_name = "has_" + fieldname
        # setattr(cls, field.checker_name, field.makechecker(fieldname))

    def __repr__(self):
        return "<%s.%s at %x>" % (self.__class__.__module__, self.__class__.__name__, id(self))

    def __eq__(self, another):
        if another is None: return False
        if type(self) != type(another): return False
        # Compare all fields
        for k in self.__model_fields__:
            if getattr(self, k) != getattr(another, k):
                return False
        return True

    def __contains__(self, fieldname):
        if fieldname.startswith("has_"): set_trace()
        return fieldname in self.__field_values__

    def __getitem__(self, fieldname):
        if fieldname not in self.__model_fields__:
            set_trace()
            raise Exception(f"Invalid field name: {fieldname}")
        return getattr(self, fieldname)

    def get(self, fieldname, on_missing = None):
        return self.__getitem__(fieldname)

    def setfield(self, fieldname, value, reject_invalid_field = False):
        if fieldname not in self.__model_fields__:
            if reject_invalid_field: 
                raise Exception(f"Invalid field name: '{fieldname}'")
        else:
            setattr(self, fieldname, value)
        return self

    def validate(self):
        """ Validates the current state of the instance."""
        for validator in self._validators:
            validator(self)
        return self

    def apply_patch(self, patch, reject_invalid_fields = False):
        for fieldname, value in patch.items():
            self.setfield(fieldname, value, reject_invalid_fields)
        return self

class ModelMeta(type):
    def __new__(cls, name, bases, dct):
        x = super().__new__(cls, name, bases, dct)

        # Evaluate FQN
        x.__fqn__ = dct.get("__fqn__", ".".join([x.__module__, name]))

        # Register all fields
        __model_fields__ = getattr(x, "__model_fields__", {}).copy()
        setattr(x, "__model_fields__", __model_fields__)
        for fieldname,entry in x.__dict__.copy().items():
            if issubclass(entry.__class__, Field):
                x.register_field(fieldname, entry)
        return x

class Model(with_metaclass(ModelMeta, ModelBase)):
    pass

class PatchModelBase(Model):
    """ Patch objects represent the "patch actions" that can be performed on the fields of a Model. """
    pass

class PatchModelMeta(ModelMeta):
    def __new__(cls, name, bases, dct):
        x = super().__new__(cls, name, bases, dct)
        model_class = getattr(x, "ModelClass", None)
        if False and not model_class and (len(bases) != 1 or bases[0] != PatchModelBase):
            set_trace()
            raise Exception("PatchModel class MUST have an ModelClass class attribute to indicate resource classes being patched.")
        return x

class PatchModel(with_metaclass(PatchModelMeta, PatchModelBase)):
    pass

class Patch(typing.Generic[typing.TypeVar("M", bound = ModelBase)]): pass

PatchType = TypeVar("PatchType")
EntryType = TypeVar("EntryType")

class PatchCommand(Union, typing.Generic[PatchType]):
    SET = Variant(PatchType)
    DELETE = Variant(None)  # No associated type

class ListPatchCommand(Union, Generic[EntryType, PatchType]):
    SET = Variant(List[EntryType])
    DELETE = Variant(None)
    REPLACE = Variant(Tuple[int, PatchType])
    INSERT = Variant(Tuple[int, PatchType])
    REMOVE = Variant(List[int])
    SWAP = Variant(Tuple[int, int])
