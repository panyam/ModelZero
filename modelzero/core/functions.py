
from ipdb import set_trace
import typing
from typing import Union
from modelzero.core import types
import inspect
from inspect import signature
from modelzero.core import exprs

class NativeFunction(exprs.Function):
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
            return_type = exprs.ensure_type(self.inspected_sig.return_annotation)

            param_types = {}
            for name,param in self.inspected_sig.parameters.items():
                # Ensure all required fields are covered in the API call
                if param.default is not inspect._empty:
                    self._param_default_values[name] = param.default
                param_types[name] = None
                if param.annotation and param.annotation is not inspect._empty:
                    annot = param.annotation
                    param_types[name] = exprs.ensure_type(annot)
            self._inspected_type = types.Type.as_func_type(param_types, return_type)

        if self.annotated_type:
            # Ensure there are no inconsistencies
            set_trace()
        return self._inspected_type
