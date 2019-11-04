
from jinja2 import Template
import datetime, typing, inspect
import sys
from modelzero.core import custom_fields as fields
from modelzero.core.models import ModelBase, PatchModelBase, PatchModel, PatchCommand, ListPatchCommand
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn
import modelzero.apigen.apispec
from ipdb import set_trace

model_class_template = Template("""
class {{class_name}} : AbstractEntity {
{%- for name, field in model_class.__model_fields__.items() %}
    var {{name}} : {{ gen.swifttype_for(field.logical_type) }} = {{ gen.default_value_for(field.logical_type) }}
{%- endfor %}
    enum CodingKeys : String, CodingKey {
    {%- for name, field in model_class.__model_fields__.items() %}
        case {{name}}
    {%- endfor %}
    }
}
""")

patch_model_class_template = Template("""
extension {{class_name}} {
    class Patch : Codable {
    {%- for name, field in patch_model.__model_fields__.items() %}
        var {{name}} : {{ gen.swifttype_for(field.logical_type) }}? = nil
    {%- endfor %}
    }
}
""")

api_method_template = Template("""
func {{ method.name }}({%- for name, param in method.kwargs.items() -%}
    {%- if loop.index0 > 0 %}, {% endif %}
    {{ name }}: {{gen.swifttype_for(method.param_annotations[name].annotation)}}
{%- endfor %}) throws -> 
    {%- if method.return_annotation -%}
        AsyncResultState<{{ gen.swifttype_for(method.return_annotation) }}>
    {%- else -%}
        AsyncResultState<Int>
    {%- endif -%} {
    var comps = makeUrlComponents()
    comps.queryItems = [
    {%- for name, param in method.query_params.items() %}
        URLQueryItem(name: "{{ name }}", value: {{ name }}),
    {%- endfor %}
    ]
    comps.path = "{{ path_prefix }}"

    let url : URL = comps.url!
    var request = URLRequest(url: url)
    request.httpMethod = "{{ http_method }}"
    {% with name,param = method.body_param %} {% if name %}
    let encoder = JSONEncoder()
    request.httpBody = try encoder.encode({{name}})
    {% endif %}{% endwith %}
    return fetchRequest(request: request)
}
""")

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

    def is_patch_type(self, logical_type):
        orig = getattr(logical_type, "__origin__", None)
        return orig is modelzero.core.models.Patch

class Generator(GeneratorBase):
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
            return "nil"
        if logical_type == str:
            return '""'
        if logical_type == typing.Any:
            return "nil"
        if fields.KeyType in (logical_type.mro()):
            return "nil"
        if logical_type == fields.URL:
            return 'URL(string: "http://")'
        if logical_type == datetime.datetime:
            return "Date(timeIntervalSince1970: 0)"
        if logical_type == list or list in (logical_type.mro()):
            return "[]"
        if logical_type == dict or dict in logical_type.mro():
            return "[:]"
        try:
            if issubclass(logical_type, ModelBase):
                # TODO - Create a "default" value?
                return "nil"
        except Exception as exc:
            set_trace()
        if issubclass(logical_type, fields.JsonField):
            return "nil"
        assert False, f"Invalid logical_type found: {logical_type}"

    def swifttype_for(self, logical_type):
        assert not isinstance(logical_type, fields.Field), "Do not pass instances of Field"
        if logical_type == bool:
            return "Bool"
        if logical_type == int:
            return "Int"
        if logical_type == float:
            return "Float"
        if logical_type == bytes:
            return "Data?"
        if logical_type == str:
            return "String"
        if logical_type == datetime.datetime:
            return "Date"
        if logical_type == typing.Any:
            return "Any?"
        if logical_type == fields.JsonField:
            return "Any?"
        if logical_type == fields.URL:
            return "URL?"
        if self.is_key_type(logical_type):
            thetype = self.resolve_generic_arg(logical_type.__args__[0])
            return f"Ref<{self.name_for_model_class(thetype)}>?"
        # if logical_type == list: return "[Any]"
        # if logical_type == dict: return "[String : Any]"
        if self.is_list_type(logical_type):
            thetype = self.resolve_generic_arg(logical_type.__args__[0])
            return f"[{self.swifttype_for(thetype)}]"
        if self.is_dict_type(logical_type):
            key_type = self.resolve_generic_arg(logical_type.__args__[0])
            val_type = self.resolve_generic_arg(logical_type.__args__[1])
            return f"[{self.swifttype_for(key_type)} : {self.swifttype_for(val_type)}]"
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
                return f"ListPatchCommand<{self.swifttype_for(entry_arg)}, {self.swifttype_for(patch_arg)}>"
            if origin is PatchCommand:
                arg = logical_type.__args__[0]
                return f"PatchCommand<{self.swifttype_for(arg)}>"
            return
        if self.is_model_class(logical_type):
            return f"{self.name_for_model_class(logical_type)}"
        assert False, f"Invalid logical_type: {logical_type}"

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

    def class_for_model_class(self, model_class):
        class_name = self.register_model_class(model_class)
        # See if class_name is taken by another model
        return model_class_template.render(gen = self,
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


    def swiftclient_for(self, router, class_name):
        """ Generate the client with method per call in the API router. """
        # See if class_name is taken by another model
        from collections import deque
        out = [f"class {class_name} : ApiBase {{"]
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
            path_prefix = path_prefix.replace(f"{{{name}}}", f"\\({name})")
        return api_method_template.render(method = method,
                                          http_method = http_method,
                                          path_prefix = path_prefix,
                                          gen = self)
