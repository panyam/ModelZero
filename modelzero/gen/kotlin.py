
from taggedunion import CaseMatcher, case
import datetime, typing, inspect
import sys
from modelzero.core import custom_fields as fields
from modelzero.core.models import ModelBase, PatchModelBase, PatchModel, PatchCommand, ListPatchCommand
from modelzero.core.entities import Entity
from modelzero.core import types
from modelzero.utils import resolve_fqn
from modelzero.gen import core as gencore
import modelzero.apigen.apispec
from ipdb import set_trace

class DefaultValue(CaseMatcher):
    __caseon__ = types.Type

    def valueOf(self, thetype : types.Type):
        return self(thetype)

    @case("opaque_type")
    def valueOfOpaqueType(self, thetype : types.OpaqueType):
        if thetype.name == "bool": return "false"
        if thetype.name in ("int", "long"): return "0"
        if thetype.name in ("float", "double"): return "0"
        if thetype.name == "bytes": return "null"
        if thetype.name == "str": return '""'
        if thetype.native_type == typing.Any: return "null"
        if thetype.native_type == datetime.datetime: return "Date()"
        if thetype.native_type == fields.URL: return 'URL("http://")'

    @case("prod_type")
    def valueOfProductType(self, thetype : types.ProductType):
        set_trace()

    @case("sum_type")
    def valueOfSumType(self, thetype : types.SumType):
        set_trace()

    @case("type_var")
    def valueOfTypeVar(self, thetype : types.TypeVar):
        set_trace()

    @case("type_ref")
    def valueOfTypeRef(self, thetype : types.TypeRef):
        set_trace()

    @case("type_app")
    def valueOfTypeApp(self, thetype : types.TypeApp):
        set_trace()
        if self.optional_type_of(logical_type):
            optional_of = self.optional_type_of(logical_type)
            return "null"
        if self.is_key_type(logical_type):
            return "null"
        if logical_type == list or list in (logical_type.mro()):
            return "emptyList()"
        if logical_type == dict or dict in logical_type.mro():
            return "emptyMap()"
        try:
            if issubclass(logical_type, ModelBase):
                # TODO - Create a "default" value?
                return "null"
        except Exception as exc:
            set_trace()
        assert False, f"Invalid logical_type found: {logical_type}"

class Generator(gencore.GeneratorBase):
    """ Generates model bindings for model to Swift.  """
    def __init__(self):
        # Swift does not have packages so we need names to be unique
        # and this uniqueness can come by not ensuring two classes globally 
        # dont have the same name *or* letting user specify an alternative name
        # 
        self.models_by_name = {}
        self.fqn_to_classname = {}
        self.fqn_to_model = {}

        # Map a modelclass fqn to its patchclass name
        self.modelclass_fqn_to_patchclass_fqn = {}
        # Map a patch class fqn to t
        self.patchclasses_by_fqn = {}

    def name_for_model_class(self, model_class):
        self.register_model_class(model_class)
        efqn = model_class.__fqn__
        if efqn not in self.fqn_to_classname:
            raise KeyError(f"{model_class}")
        return self.fqn_to_classname[efqn]

    def register_model_class(self, model_class, class_name = None):
        efqn = model_class.__fqn__
        f2cn = self.fqn_to_classname.get(efqn, None)
        class_name = class_name or model_class.__name__
        curr_eclass = self.models_by_name.get(class_name, None)
        if curr_eclass and self.models_by_name[class_name].__fqn__ != efqn:
            set_trace()
            raise Exception(f"Class name '{class_name}' already maps to a different entity class: {curr_eclass}")
        if f2cn and f2cn != class_name:
            raise Exception(f"Entity class {model_class} is already mapped to {class_name}, Trying to remap to: {f2cn}")
        if not curr_eclass:
            self.models_by_name[class_name] = model_class
        if not f2cn:
            self.fqn_to_classname[efqn] = class_name
        return self.fqn_to_classname[efqn]

    def resolve_fqn_or_model(self, fqn_or_model):
        model_class = fqn_or_model
        if type(fqn_or_model) is str:
            if fqn_or_model not in self.fqn_to_model:
                # resolve it
                resolved, model_class = resolve_fqn(fqn_or_model)
                self.fqn_to_model[fqn_or_model] = model_class
            else:
                model_class = self.fqn_to_model[fqn_or_model]
        if not issubclass(model_class, ModelBase):
            raise(f"{model_class} is not a Model")
        return model_class

    def default_value_for(self, logical_type):
        assert not isinstance(logical_type, fields.Field), "Do not pass instances of Field"
        if logical_type == bool:
            return "false"
        if logical_type == int:
            return "0"
        if logical_type == float:
            return "0"
        if logical_type == bytes:
            return "null"
        if logical_type == str:
            return '""'
        if logical_type == typing.Any:
            return "null"
        if self.optional_type_of(logical_type):
            optional_of = self.optional_type_of(logical_type)
            return "null"
        if self.is_key_type(logical_type):
            return "null"
        if logical_type == fields.URL:
            return 'URL("http://")'
        if logical_type == datetime.datetime:
            return "Date()"
        if logical_type == list or list in (logical_type.mro()):
            return "emptyList()"
        if logical_type == dict or dict in logical_type.mro():
            return "emptyMap()"
        try:
            if issubclass(logical_type, ModelBase):
                # TODO - Create a "default" value?
                return "null"
        except Exception as exc:
            set_trace()
        if issubclass(logical_type, fields.JsonField):
            return "null"
        assert False, f"Invalid logical_type found: {logical_type}"

    def code_for_member_extraction(self, mapname, fieldname, fieldtype):
        out = []
        optional_of = self.optional_type_of(fieldtype)
        varvalue = f"""{mapname}["{fieldname}"]"""
        if optional_of:
            # Add code to check field exists
            out.append(f"""if ({mapname}.containsKey("{fieldname}")) """)
            out.append(f"""    {fieldname} = { self.converter_call(fieldtype, varvalue) }""")
        else:
            out.append(f"""if (!{mapname}.containsKey("{fieldname}")) """)
            out.append(f"""    throw IllegalArgumentException("Expected field '{fieldname}'")""")
            out.append(f"""{fieldname} = { self.converter_call(fieldtype, varvalue) }""")

        return "\n".join(out)

    def converter_call(self, logical_type, varvalue):
        assert not isinstance(logical_type, fields.Field), "Do not pass instances of Field"
        # TODO - need to make this passable too
        # if logical_type == list: return "[Any]"
        # if logical_type == dict: return "[String : Any]"
        if logical_type == bool:
            return f"boolFromAny({varvalue}!!)"
        if logical_type == int:
            return f"intFromAny({varvalue}!!)"
        if logical_type == float:
            return f"doubleFromAny({varvalue}!!)"
        if logical_type == str:
            return f"stringFromAny({varvalue}!!)"
        if logical_type == typing.Any:
            return varvalue
        if logical_type == fields.JsonField:
            return varvalue
        if logical_type == datetime.datetime:
            return f"dateFromAny({varvalue}!!)"
        if self.optional_type_of(logical_type):
            optional_of = self.optional_type_of(logical_type)
            return self.converter_call(optional_of, varvalue)
        if self.is_key_type(logical_type):
            thetype = self.resolve_generic_arg(logical_type.__args__[0])
            # param = <{self.name_for_model_class(thetype)}>
            return f"refFromAny<{self.name_for_model_class(thetype)}>({varvalue}!!)"
        if logical_type == bytes:
            return "bytesFromAny"
        if logical_type == fields.URL:
            return f"urlFromAny({varvalue}!!)"
        if self.is_model_class(logical_type):
            return f"{self.name_for_model_class(logical_type)}({varvalue} as DataMap)"
        if self.is_patch_model_class(logical_type):
            model_class = logical_type.ModelClass
            return f"{self.name_for_model_class(model_class)}.Patch({varvalue})"
        if self.is_list_type(logical_type):
            childtype = self.resolve_generic_arg(logical_type.__args__[0])
            return f"""({varvalue} as List<Any>).map {{
                {self.converter_call(childtype, "it")}
            }}
            """
        if self.is_dict_type(logical_type):
            key_type = self.resolve_generic_arg(logical_type.__args__[0])
            val_type = self.resolve_generic_arg(logical_type.__args__[1])
            return f"Map<{self.kotlintype_for(key_type)}, {self.kotlintype_for(val_type)}>"
        set_trace()
        return f"{converter_name}({varvalue})"
        
    def kotlintype_for(self, logical_type):
        assert not isinstance(logical_type, fields.Field), "Do not pass instances of Field"
        if logical_type == bool:
            return "Boolean"
        if logical_type == int:
            return "Int"
        if logical_type == float:
            return "double"
        if logical_type == bytes:
            return "Data"
        if logical_type == str:
            return "String"
        if logical_type == datetime.datetime:
            return "Date"
        if logical_type == typing.Any:
            return "Any"
        if logical_type == fields.JsonField:
            return "Any"
        if logical_type == fields.URL:
            return "URL"
        if self.optional_type_of(logical_type):
            optional_of = self.optional_type_of(logical_type)
            return f"{self.kotlintype_for(optional_of)}?"
        if self.is_key_type(logical_type):
            thetype = self.resolve_generic_arg(logical_type.__args__[0])
            return f"Ref<{self.name_for_model_class(thetype)}>"
        # if logical_type == list: return "[Any]"
        # if logical_type == dict: return "[String : Any]"
        if self.is_list_type(logical_type):
            thetype = self.resolve_generic_arg(logical_type.__args__[0])
            return f"List<{self.kotlintype_for(thetype)}>"
        if self.is_dict_type(logical_type):
            key_type = self.resolve_generic_arg(logical_type.__args__[0])
            val_type = self.resolve_generic_arg(logical_type.__args__[1])
            return f"Map<{self.kotlintype_for(key_type)}, {self.kotlintype_for(val_type)}>"
        if self.is_patch_model_class(logical_type):
            model_class = logical_type.ModelClass
            return f"{self.name_for_model_class(model_class)}.Patch"
        if hasattr(logical_type, "__origin__"): # This is a generic type application
            origin = logical_type.__origin__
            if self.is_patch_type(logical_type):
                patch_type = self.patch_model_for(logical_type.__args__[0])
                model_class = patch_type.ModelClass
                return f"{self.name_for_model_class(model_class)}.Patch"
            if origin is ListPatchCommand:
                entry_arg = logical_type.__args__[0]
                patch_arg = logical_type.__args__[1]
                return f"ListPatchCommand<{self.kotlintype_for(entry_arg)}, {self.kotlintype_for(patch_arg)}>"
            if origin is PatchCommand:
                arg = logical_type.__args__[0]
                return f"PatchCommand<{self.kotlintype_for(arg)}>"
            return
        if self.is_model_class(logical_type):
            return f"{self.name_for_model_class(logical_type)}"
        set_trace()
        assert False, f"Invalid logical_type: {logical_type}"

    def class_for_model_class(self, model_class):
        class_name = self.register_model_class(model_class)
        # See if class_name is taken by another model
        return self.load_template("kotlin/model_class").render(gen = self,
                    model_class = model_class,
                    class_name = class_name)

    def class_for_patch_model_class(self, model_class):
        class_name = self.register_model_class(model_class)
        # See if class_name is taken by another model
        patch_model = self.patch_model_for(model_class)
        return patch_model_class_template.render(gen = self,
                    model_class = model_class,
                    class_name = class_name,
                    patch_model = patch_model)


    def kotlinclient_for(self, router, class_name):
        """ Generate the client with method per call in the API router. """
        # See if class_name is taken by another model
        from collections import deque
        out = [f"class {class_name}(httpClient : HttpClient) : JBClient(httpClient) {{"]
        def visit(r, path = ""):
            for httpmethod,method in r.methods.items():
                out.append(self.func_for_router_method(httpmethod, method, path))

            for prefix,child in r.children:
                visit(child, path + prefix)
        visit(router, "/")
        out.append("}")
        return "\n".join(out)

    def func_for_router_method(self, http_method, method, prefix):
        path_prefix = prefix
        for name, param in method.patharg_params.items():
            path_prefix = path_prefix.replace(f"{{{name}}}", f"${name}")
        return self.load_template("kotlin/api_method").render(method = method,
                                          http_method = http_method,
                                          path_prefix = path_prefix,
                                          gen = self)
