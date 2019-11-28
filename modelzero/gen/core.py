
import jinja2, os
from jinja2 import StrictUndefined
from jinja2 import Template
import datetime, typing, inspect
import sys
from modelzero.core import custom_fields as fields
from modelzero.core import types
from modelzero.core.records import Record, RecordBase
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn, camelCase
import modelzero.apigen.apispec
from ipdb import set_trace

class GeneratorBase(object):
    def __init__(self):
        self.streams = {}

    def close_all_streams(self):
        pass

    def resolve_generic_arg(self, arg):
        if type(arg) is typing.ForwardRef:
            fqn_or_eclass = arg.__forward_arg__
            result = self.resolve_fqn_or_model(fqn_or_eclass)
        else:
            result = arg
        return result

    def is_leaf_type(self, logical_type):
        if not logical_type: return False
        return logical_type in (bool, int, float, bytes, str, datetime.datetime, fields.URL, typing.Any) or self.is_key_type(logical_type)

    def is_list_type(self, logical_type):
        if not logical_type: return False
        return logical_type.is_type_app and logical_type.origin_type.is_opaque_type and logical_type.origin_type.name == "List"

    def is_key_type(self, logical_type):
        if not logical_type: return False
        return fields.KeyType in logical_type.mro()

    def is_dict_type(self, logical_type):
        if not logical_type: return False
        return dict in logical_type.mro()

    def is_patch_record_class(self, logical_type):
        if not logical_type: return False
        try:
            return issubclass(logical_type, PatchRecordBase)
        except Exception as exc:
            return False

    def is_record_class(self, logical_type):
        if not logical_type: return False
        try:
            return issubclass(logical_type, RecordBase) and not self.is_patch_record_class(logical_type)
        except Exception as exc:
            if type(logical_type) is not types.Type:
                set_trace()
            return False

    def optional_type_of(self, logical_type):
        type_app = None
        if not self.is_union_type(logical_type): return None
        orig = getattr(logical_type, "__origin__", None)
        args = logical_type.__args__
        if len(args) != 2 or type(None) not in args:
            set_trace()
            return None
        return args[0] or args[1]

    def is_union_type(self, logical_type):
        if not logical_type: return False
        orig = getattr(logical_type, "__origin__", None)
        return orig is typing.Union

    def is_patch_type(self, logical_type):
        if not logical_type: return False
        orig = getattr(logical_type, "__origin__", None)
        return orig is modelzero.core.models.Patch

    def patch_model_for(self, record_class):
        assert issubclass(record_class, RecordBase), f"{record_class} must be a subclass of RecordBase"
        assert not issubclass(record_class, PatchRecordBase), f"{record_class} cannot be a PatchModel instance"
        # What should be the name of a Patch class?
        # Our patch classes are of the form "Patch[Model]"
        # while Model has a name, there is no name for Patch[Model]
        # For now make this manual and part of the inputs into the code gen
        # later we can infer this
        """
        pclass_name = ???
        if pclass_name exists in self.pa
        patch_class = create_the_class(with_
        """
        patch_record_class, newcreated = self.ensure_patch_model(record_class)
        if newcreated:
            for name,field in record_class.__record_metadata__.items():
                logical_type = field.logical_type
                newfield = None
                if self.is_leaf_type(logical_type):
                    newfield = fields.NativeField(PatchCommand[logical_type])
                elif self.is_list_type(logical_type):
                    assert logical_type.__origin__ is list
                    child_arg = self.resolve_generic_arg(logical_type.__args__[0])
                    entry_type = child_arg
                    if self.is_leaf_type(child_arg):
                        patch_type = child_arg
                    else:
                        patch_type = self.patch_model_for(child_arg)
                    child_type = ListPatchCommand[entry_type, patch_type]
                    newfield = fields.ListField(child_type)
                else:
                    assert False, f"Cannot handle field type: {field}"
                patch_record_class.register_field(name, newfield)
        return patch_record_class

    def ensure_patch_model(self, record_class):
        newcreated = False
        mfqn = record_class.__fqn__
        if mfqn not in self.modelclass_fqn_to_patchclass_fqn:
            self.modelclass_fqn_to_patchclass_fqn[mfqn] = f"{mfqn}.PatchModel"
        patchclass_fqn = self.modelclass_fqn_to_patchclass_fqn[mfqn]
        if patchclass_fqn not in self.patchclasses_by_fqn:
            newcreated = True
            patch_model = type(f"{record_class.__name__}_PatchModel",
                            (PatchModel,),
                            dict(RecordClass = record_class,
                                __fqn__ = patchclass_fqn))
            self.patchclasses_by_fqn[patchclass_fqn] = patch_model
        return self.patchclasses_by_fqn[patchclass_fqn], newcreated

    def load_template(self, tpl_name):
        location = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "templates")
        templateLoader = jinja2.FileSystemLoader(searchpath=location)
        templateEnv = jinja2.Environment(loader=templateLoader)
        templateEnv.undefined = StrictUndefined
        templateEnv.globals['camelCase'] = camelCase
        TEMPLATE_FILE = f"{tpl_name}.tpl"
        return templateEnv.get_template(TEMPLATE_FILE)

    def dict_get(self, obj, key, is_str = True):
        if is_str:
            return f"""{obj}["{key}"]"""
        else:
            return f"{obj}[{key}]"
