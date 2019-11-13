
from ipdb import set_trace
from collections import defaultdict
from typing import Generic, TypeVar
from modelzero.utils import get_param, ensure_date, with_metaclass
from modelzero.core.store import Query
from modelzero.core.entities import Entity
from functools import wraps
from . import errors

import logging
log = logging.getLogger(__name__)

T = TypeVar("T")

class MethodValidator(object):
    def __call__(self, input, *args, **kwargs):
        return input

def ensure_access(target_member, accessor, permission : str):
    """
    Return true if *accessor* can access the target_member for a particular permission.
    If not a NotAllowed exception is raised.
    """
    if not permission: 
        return True
    if accessor is None:
        raise errors.NotAllowed("Accessor not found")
    if target_member != accessor:
        raise errors.NotAllowed("Access not allowed for permission '%s'" % permission)
    return True

class EngineBase(object):
    RecordClass = Entity
    def __init__(self, datastore, dev_mode = None):
        self.is_dev_mode = dev_mode or False
        self.datastore = datastore
        self.table = datastore.get_table(self.record_class)

    @property
    def record_class(self):
        return self.RecordClass

class EngineMethod(object):
    def __new__(cls, *args, **kwargs):
        # Do not create duplicate EngineMethods wrappign each other
        # flatmap it baby!
        if len(args) > 0 and issubclass(args[0].__class__, EngineMethod):
            return args[0]
        return super().__new__(cls)

    def __init__(self, target_method):
        if issubclass(target_method.__class__, EngineMethod):
            # DO nothing because we are wrapping ourselves!
            return 
        import inspect
        self.__name__ = target_method.__name__
        self.signature = inspect.signature(target_method)
        self.method_params = list(self.signature.parameters.keys())
        self.target_method = target_method
        self.record_class = None
        self.validators = []

    def __get__(self, instance, klass):
        if instance is None:
            # Class method was requested
            set_trace()
            return self.make_unbound(klass)
        return self.make_bound(instance)

    def __call__(self, *args, **kwargs):
        """ Called when decorating a plain method. """
        set_trace()

    def make_unbound(self, klass):
        @wraps(self.target_method)
        def wrapper(*args, **kwargs):
            '''This documentation will vanish :)'''
            raise TypeError(
                f'unbound method {self.target_method.__name__}() '
                 'must be called with {klass.__name__} instance '
                 'as first argument (got nothing instead)')
        return wrapper

    def make_bound(self, instance):
        @wraps(self.target_method)
        def wrapper(*args, **kwargs):
            # Apply validators
            return self._invoke_target(instance, *args, **kwargs)
        # This instance does not need the descriptor anymore,
        # let it find the wrapper directly next time:
        # setattr(instance, self.target_method.__name__, wrapper)
        return wrapper

    def _get_param(self, param_name, *args, **kwargs):
        param = None
        if param_name in kwargs:
            param = kwargs[param_name]
        else:
            # see if it is in args
            for i,mp in enumerate(self.method_params):
                if mp == param_name:
                    paramIndex = i - 1
                    if paramIndex < len(args):
                        param = args[paramIndex]
                    break
        if param is None:
            raise errors.ValidationError(f"Validator applied to no existent parameter: '{param_name}', in method ({self.target_method})")
        return param

    def _invoke_target(self, instance, *args, **kwargs):
        param_errors = defaultdict(lambda : list())
        method_errors = defaultdict(lambda : list())
        ignore_params = set()
        for param_name, validator, vargs, vkwargs in self.validators:
            # If a parameter already has errors do not apply another
            # validator on this param again.
            if param_name not in ignore_params:
                param = self._get_param(param_name, *args, **kwargs)
                try:
                    param = validator(param, *vargs, **vkwargs)
                except StopIteration as si:
                    # A validator can raise  StopIteration for all parameters
                    # it will want to stop validating
                    if not si.value:
                        ignore_params.add(param_name)
                    else:
                        for pname in si.args:
                            ignore_params.add(pname)
                except errors.ValidationError as ve:
                    # Add the validation error for this param
                    logging.error(f"Validation Error in method "
                                    "({self.target_method.__name__}) "
                                    "for ('{param_name}' = {param}): {ve.message}")
                    param_errors[param_name].append(ve)
        if param_errors:
            raise ValidationError("Validation failure", param_errors)
        else:
            return self.target_method(instance, *args, **kwargs)

    @classmethod
    def ValidateParam(cls, param_name, predicate, *args, **kwargs):
        def decorator(func):
            if not issubclass(func.__class__, EngineMethod):
                func = EngineMethod(func)
            func.add_validator(param_name, predicate, *args, **kwargs)
            return func
        return decorator

    def add_validator(self, param_name, predicate, *args, **kwargs):
        self.validators.append((param_name, predicate, args, kwargs))

class EngineMeta(type):
    """ A metaclass for services for to interact with entities. """
    def __new__(cls, name, bases, dct):
        x = super().__new__(cls, name, bases, dct)
        record_class = getattr(x, "RecordClass", None)
        if not record_class:
            raise Exception("Service class MUST have an RecordClass class attribute to indicate resource classes being serviced.")

        x.__service_methods__ = getattr(x, "__service_methods__", {}).copy()
        newentrys = {}
        for name,entry in x.__dict__.items():
            if not issubclass(entry.__class__, EngineMethod): continue
            x.__service_methods__[name] = entry
            entry.record_class = record_class
        return x

class Engine(with_metaclass(EngineMeta, EngineBase)):
    pass
