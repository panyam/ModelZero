
from jinja2 import Template
import datetime, typing, inspect
import sys
from modelzero.core import custom_fields as fields
from modelzero.core.models import ModelBase, PatchModelBase, PatchModel, PatchCommand, ListPatchCommand
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn
from modelzero.gen import core as gencore
import modelzero.apigen.apispec
from ipdb import set_trace

record_class_template = Template("""
class {{class_name}} : AbstractEntity {
{%- for name, field in record_class.__record_metadata__.items() %}
    var {{name}} : {{ gen.swifttype_for(field.logical_type) }} = {{ gen.default_value_for(field.logical_type) }}
{%- endfor %}
    enum CodingKeys : String, CodingKey {
    {%- for name, field in record_class.__record_metadata__.items() %}
        case {{name}}
    {%- endfor %}
    }
}
""")

patch_record_class_template = Template("""
extension {{class_name}} {
    class Patch : Codable {
    {%- for name, field in patch_model.__record_metadata__.items() %}
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
        URLQueryItem(name: "{{ name }}", value: "\({{ name }})"),
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

    def name_for_record_class(self, record_class):
        self.register_record_class(record_class)
        efqn = record_class.__fqn__
        if efqn not in self.fqn_to_classname:
            raise KeyError(f"{record_class}")
        return self.fqn_to_classname[efqn]

    def register_record_class(self, record_class, class_name = None):
        efqn = record_class.__fqn__
        f2cn = self.fqn_to_classname.get(efqn, None)
        class_name = class_name or record_class.__name__
        curr_eclass = self.models_by_name.get(class_name, None)
        if curr_eclass and self.models_by_name[class_name].__fqn__ != efqn:
            set_trace()
            raise Exception(f"Class name '{class_name}' already maps to a different entity class: {curr_eclass}")
        if f2cn and f2cn != class_name:
            raise Exception(f"Entity class {record_class} is already mapped to {class_name}, Trying to remap to: {f2cn}")
        if not curr_eclass:
            self.models_by_name[class_name] = record_class
        if not f2cn:
            self.fqn_to_classname[efqn] = class_name
        return self.fqn_to_classname[efqn]

    def resolve_fqn_or_model(self, fqn_or_model):
        record_class = fqn_or_model
        if type(fqn_or_model) is str:
            if fqn_or_model not in self.fqn_to_model:
                # resolve it
                resolved, record_class = resolve_fqn(fqn_or_model)
                self.fqn_to_model[fqn_or_model] = record_class
            else:
                record_class = self.fqn_to_model[fqn_or_model]
        if not issubclass(record_class, ModelBase):
            raise(f"{record_class} is not a Model")
        return record_class

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
            return f"Ref<{self.name_for_record_class(thetype)}>?"
        # if logical_type == list: return "[Any]"
        # if logical_type == dict: return "[String : Any]"
        if self.is_list_type(logical_type):
            thetype = self.resolve_generic_arg(logical_type.__args__[0])
            return f"[{self.swifttype_for(thetype)}]"
        if self.is_dict_type(logical_type):
            key_type = self.resolve_generic_arg(logical_type.__args__[0])
            val_type = self.resolve_generic_arg(logical_type.__args__[1])
            return f"[{self.swifttype_for(key_type)} : {self.swifttype_for(val_type)}]"
        if self.is_patch_record_class(logical_type):
            record_class = logical_type.RecordClass
            return f"{self.name_for_record_class(record_class)}.Patch"
        if hasattr(logical_type, "__origin__"): # This is a generic type application
            origin = logical_type.__origin__
            if self.is_patch_type(logical_type):
                patch_type = self.patch_model_for(logical_type.__args__[0])
                record_class = patch_type.RecordClass
                return f"{self.name_for_record_class(record_class)}.Patch"
            if origin is ListPatchCommand:
                entry_arg = logical_type.__args__[0]
                patch_arg = logical_type.__args__[1]
                return f"ListPatchCommand<{self.swifttype_for(entry_arg)}, {self.swifttype_for(patch_arg)}>"
            if origin is PatchCommand:
                arg = logical_type.__args__[0]
                return f"PatchCommand<{self.swifttype_for(arg)}>"
            return
        if self.is_record_class(logical_type):
            return f"{self.name_for_record_class(logical_type)}"
        set_trace()
        assert False, f"Invalid logical_type: {logical_type}"

    def class_for_record_class(self, record_class):
        class_name = self.register_record_class(record_class)
        # See if class_name is taken by another model
        return record_class_template.render(gen = self,
                    record_class = record_class,
                    class_name = class_name)

    def class_for_patch_record_class(self, record_class):
        class_name = self.register_record_class(record_class)
        # See if class_name is taken by another model
        patch_model = self.patch_model_for(record_class)
        return patch_record_class_template.render(gen = self,
                    record_class = record_class,
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
