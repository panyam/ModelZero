
from ipdb import set_trace
import typing
from modelzero.core import types

class FieldPath(object):
    def __init__(self, value : typing.Union[str, typing.List[str]]):
        if type(value) is str:
            value = [v.strip() for v in value.split("/") if v.strip()]
        self.parts = value

class Derivation(object):
    def __init__(self, fqn = None, **input_types : typing.Dict[str, types.Type]):
        self._inputs = {k: types.ensure_type(v) for k, v in input_types.items()}
        self._derived_type = None
        self._name = self._fqn = None
        if fqn and fqn.strip():
            parts = [f.strip() for f in fqn.split(".") if f.strip()]
            self._fqn = ".".join(parts)
            self._name = parts[-1]

    @property
    def name(self): return self._name

    @property
    def fqn(self): return self._fqn

    def get_input(self, name : str) -> types.Type:
        return self._inputs[name]

    def include(self, source : str, field_path : FieldPath = None):
        """ Includes one or all fields from the source type at the root level
        of this derivation.
        """
        pass

    def exclude(self, source_field_path : FieldPath):
        """ Removes particular field paths. """
        pass

    def select(self, source_field_path : FieldPath,
               target : str = None, *transformers):
        """ Selects a particular source field as a field in the current root.

        This allows selection of a field in the source type (at an arbitrary depth) and placed at the top level of this derivation.  The target field is same as the source field name by default (and subject to error if duplicate).  The target field can be aliased to a different name optionally (say to avoid duplications).
        """
        pass

    def __call__(self, *args, **kwargs):
        """ A derivation must also be callable since it is possible it is also used as a Transformer! """
        pass

    @property
    def derived_type(self):
        """ Returns the type that corresponds the result of the derivations """
        if self._derived_type is None:
            self._derived_type = types.Type()
            classdict = dict(__fqn__ = self.fqn)
            rec_class = types.RecordType.new_record_class(self.name, **classdict)
            rec_type = types.RecordType(rec_class)
            self._derived_type.record_type = rec_type
        return self._derived_type
