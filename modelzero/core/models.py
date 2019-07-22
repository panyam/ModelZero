
from ipdb import set_trace
import datetime
import typing
from typing import TypeVar, Generic, List
import datetime
from modelzero.core.fields import *
from modelzero.utils import with_metaclass

class ModelBase(object):
    """ Models are our base of all objects that need a representation. """
    def __init__(self, **kwargs):
        self.__field_values__ = {}
        self._validators = []
        self.apply_patch(kwargs, reject_invalid_fields = True)

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
    __model_registry__ = {}
    def __new__(cls, name, bases, dct):
        x = super().__new__(cls, name, bases, dct)
        x.__model_registry__ = ModelMeta.__model_registry__

        __model_fields__ = getattr(x, "__model_fields__", {}).copy()
        setattr(x, "__model_fields__", __model_fields__)
        newfields = {}
        for fieldname,field in x.__dict__.items():
            if not issubclass(field.__class__, Field): continue

            # What do we do if the field is already present 
            # (ie via a base class or via a duplicate declaration)?
            field.field_name = fieldname
            __model_fields__[fieldname] = field
            if not field.checker_name:
                field.checker_name = "has_" + fieldname
            newfields[field.checker_name] = field.makechecker(fieldname)
            # newfields[fieldname] = field.makeproperty(fieldname)

        # Set the new methods/fields that we have
        for k,v in newfields.items(): setattr(x,k,v)

        fqn = ".".join([x.__module__, name]) # getattr(x, "__fqn__", fqn)
        if False and fqn in ModelMeta.__model_registry__:
            raise Exception("Duplicate definition of model: " + fqn + 
                            ".  Please use a different name or provide a __fqn__ attr")
        ModelMeta.__model_registry__[fqn] = x
        x.__fqn__ = fqn
        return x

class Model(with_metaclass(ModelMeta, ModelBase)):
    pass
