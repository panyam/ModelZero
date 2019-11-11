
import jinja2, os
from jinja2 import Template
import datetime, typing, inspect
import sys
from modelzero.core import custom_fields as fields
from modelzero.core.models import ModelBase, PatchModelBase, PatchModel, PatchCommand, ListPatchCommand
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn
import modelzero.apigen.apispec
from ipdb import set_trace

class GeneratorBase(object):
    def resolve_generic_arg(self, arg):
        if type(arg) is typing.ForwardRef:
            fqn_or_eclass = arg.__forward_arg__
            result = self.resolve_fqn_or_model(fqn_or_eclass)
        else:
            result = arg
        return result

    def is_leaf_type(self, logical_type):
        return logical_type in (bool, int, float, bytes, str, datetime.datetime, fields.URL, typing.Any) or self.is_key_type(logical_type)

    def is_list_type(self, logical_type):
        return list in logical_type.mro()

    def is_key_type(self, logical_type):
        return fields.KeyType in logical_type.mro()

    def is_dict_type(self, logical_type):
        return dict in logical_type.mro()

    def is_patch_model_class(self, logical_type):
        try:
            return issubclass(logical_type, PatchModelBase)
        except Exception as exc:
            return False

    def is_model_class(self, logical_type):
        try:
            return issubclass(logical_type, ModelBase) and not self.is_patch_model_class(logical_type)
        except Exception as exc:
            return False

    def optional_type_of(self, logical_type):
        if not self.is_union_type(logical_type): return None
        orig = getattr(logical_type, "__origin__", None)
        args = logical_type.__args__
        if len(args) != 2 or type(None) not in args:
            set_trace()
            return None
        return args[0] or args[1]

    def is_union_type(self, logical_type):
        orig = getattr(logical_type, "__origin__", None)
        return orig is typing.Union

    def is_patch_type(self, logical_type):
        orig = getattr(logical_type, "__origin__", None)
        return orig is modelzero.core.models.Patch

    def patch_model_for(self, model_class):
        assert issubclass(model_class, ModelBase), f"{model_class} must be a subclass of Modelbase"
        assert not issubclass(model_class, PatchModelBase), f"{model_class} cannot be a PatchModel instance"
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
        patch_model_class, newcreated = self.ensure_patch_model(model_class)
        if newcreated:
            for name,field in model_class.__model_fields__.items():
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
                patch_model_class.register_field(name, newfield)
        return patch_model_class

    def ensure_patch_model(self, model_class):
        newcreated = False
        mfqn = model_class.__fqn__
        if mfqn not in self.modelclass_fqn_to_patchclass_fqn:
            self.modelclass_fqn_to_patchclass_fqn[mfqn] = f"{mfqn}.PatchModel"
        patchclass_fqn = self.modelclass_fqn_to_patchclass_fqn[mfqn]
        if patchclass_fqn not in self.patchclasses_by_fqn:
            newcreated = True
            patch_model = type(f"{model_class.__name__}_PatchModel",
                            (PatchModel,),
                            dict(ModelClass = model_class,
                                __fqn__ = patchclass_fqn))
            self.patchclasses_by_fqn[patchclass_fqn] = patch_model
        return self.patchclasses_by_fqn[patchclass_fqn], newcreated

    def load_template(self, tpl_name):
        location = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "templates")
        templateLoader = jinja2.FileSystemLoader(searchpath=location)
        templateEnv = jinja2.Environment(loader=templateLoader)
        TEMPLATE_FILE = f"{tpl_name}.tpl"
        return templateEnv.get_template(TEMPLATE_FILE)

    def dict_get(self, obj, key, is_str = True):
        if is_str:
            return f"""{obj}["{key}"]"""
        else:
            return f"{obj}[{key}]"
