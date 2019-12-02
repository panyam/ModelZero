
from ipdb import set_trace
import typing
from typing import List, Union, Dict, Tuple
from modelzero.core import types
from modelzero.core.custom_types import MZTypes
import inspect
from inspect import signature

def ensure_type(t):
    if t in (None, inspect._empty):
        return None
    if t is str:
        return MZTypes.String
    if t is int:
        return MZTypes.Int
    if t is bool:
        return MZTypes.Bool
    if type(t) is typing._GenericAlias:
        if t.__origin__ == list:
            return MZTypes.List[ensure_type(t.__args__[0])]
        if t.__origin__ == dict:
            return MZTypes.Map[ensure_type(t.__args__[0]), ensure_type(t.__args__[1])]
        if t.__origin__ == typing.Union:
            if len(t.__args__) == 2 and type(None) in t.__args__:
                optional_of = t.__args__[0] or t.__args__[1]
                return MZTypes.Optional[ensure_type(optional_of)]
            else:
                children = [ensure_type(ta) for ta in t.__args__]
                return types.Type.as_sum_type(None, *children)
        set_trace()
        a = 3
    try:
        return types.ensure_type(t)
    except Exception as exc:
        raise exc

class Function(object):
    def __init__(self):
        self._param_default_values = {}

    def has_default_value(self, param_name):
        return param_name in self._param_default_values

    def set_default_value(self, param_name, value):
        self._param_default_values[param_name] = value

    @property
    def return_type(self):
        return self.func_type.return_type

    def has_param(self, name):
       return name in self.func_type.param_types

    def param(self, name):
        return self.func_type.param_types[name]

    @property
    def param_names(self):
        return self.func_type.param_types.keys()

class NativeFunction(Function):
    """ Commands that produce evaluated fields. """
    def __init__(self, func_or_fqn : Union[str, "function"],
                 annotated_type : types.Type = None):
        super().__init__()
        if type(func_or_fqn) is str:
            self._name = func_or_fqn
            self._function = resolve_fqn(func_or_fqn)
        else:
            self._function = func_or_fqn
            self._name = func_or_fqn.__name__
        self.annotated_type = annotated_type
        self.inspected_sig = signature(self._function)
        self._inspected_type = None

    @property
    def target(self):
        return self._function

    @property
    def fqn(self):
        return f"{self.target.__module__}.{self.name}"

    @property
    def name(self):
        return self._name

    @property
    def func_type(self):
        if not self._inspected_type:
            return_type = ensure_type(self.inspected_sig.return_annotation)

            param_types = {}
            for name,param in self.inspected_sig.parameters.items():
                # Ensure all required fields are covered in the API call
                if param.default is not inspect._empty:
                    self._param_default_values[name] = param.default
                param_types[name] = None
                if param.annotation and param.annotation is not inspect._empty:
                    annot = param.annotation
                    param_types[name] = ensure_type(annot)
            self._inspected_type = types.Type.as_func_type(param_types, return_type)

        if self.annotated_type:
            # Ensure there are no inconsistencies
            set_trace()
        return self._inspected_type
