
from ipdb import set_trace
from collections import defaultdict
from functools import wraps
from . import errors

import logging
log = logging.getLogger(__name__)

def ValidateParam(param_name, predicate, *args, **kwargs):
    def decorator(func):
        is_first = not hasattr(func, "__param_validator__")
        if is_first:
            func.__param_validator__ = ParamValidator(func)
        pv = func.__param_validator__
        pv.add_validator(param_name, predicate, *args, **kwargs)

        if not is_first:
            return func

        @wraps(func)
        def wrapper(*args, **kwargs):
            return pv(*args, **kwargs)
        return wrapper
    return decorator

class ParamValidator(object):
    def __new__(cls, *args, **kwargs):
        # Do not create duplicate ParamValidators wrapping each other
        # flatmap it baby!
        if len(args) > 0 and issubclass(args[0].__class__, ParamValidator):
            return args[0]
        return super().__new__(cls)

    def __init__(self, target_method):
        if issubclass(target_method.__class__, ParamValidator):
            # DO nothing because we are wrapping ourselves!
            return 
        import inspect
        self.__name__ = target_method.__name__
        self.signature = inspect.signature(target_method)
        self.method_params = list(self.signature.parameters.keys())
        self.target_method = target_method
        self.validators = []

    def add_validator(self, param_name, predicate, *args, **kwargs):
        self.validators.append((param_name, predicate, args, kwargs))

    def __call__(self, *args, **kwargs):
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
            raise errors.ValidationError("Validation failure", param_errors)
        else:
            return self.target_method(*args, **kwargs)
            
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
