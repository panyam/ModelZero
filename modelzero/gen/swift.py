
from jinja2 import Template
import datetime, typing, inspect
import sys
from modelzero.core import custom_fields as fields
from modelzero.core.models import ModelBase
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn
import modelzero.apigen.apispec
from ipdb import set_trace

entity_class_template = Template("""
class {{class_name}} : AbstractEntity {
{%- for name, field in entity_class.__model_fields__.items() %}
    var {{name}} : {{ gen.swifttype_for(field.logical_type) }} = {{ gen.default_value_for(field.logical_type) }}
{%- endfor %}
}
""")

api_method_template = Template("""
func {{ method.name }}(
{%- for name, param in method.kwargs.items() -%}
    {%- if loop.index0 > 0 %}, {% endif %}
    {{ name }}: {{gen.swifttype_for(method.param_annotations[name].annotation)}}
{%- endfor %}) {% if method.return_annotation %} -> AsyncResultState<{{ gen.swifttype_for(method.return_annotation) }}> {% endif %} {
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
    request.body = toJson({{ name }})
    {% endif %}{% endwith %}
    return fetchRequest(request: request)
}
""")

class Generator(object):
    """ Generates model bindings for entities to Swift.  """
    def __init__(self):
        # Swift does not have packages so we need names to be unique
        # and this uniqueness can come by not ensuring two classes globally 
        # dont have the same name *or* letting user specify an alternative name
        # for an entity
        self.name_to_entities = {}
        self.fqn_to_classname = {}
        self.fqn_to_entity = {}

    def name_for_entity_class(self, entity_class):
        self.register_entity_class(entity_class)
        efqn = entity_class.__fqn__
        if efqn not in self.fqn_to_classname:
            raise KeyError(f"{entity_class}")
        return self.fqn_to_classname[efqn]

    def register_entity_class(self, entity_class, class_name = None):
        efqn = entity_class.__fqn__
        f2cn = self.fqn_to_classname.get(efqn, None)
        class_name = class_name or entity_class.__name__
        curr_eclass = self.name_to_entities.get(class_name, None)
        if curr_eclass and self.name_to_entities[class_name].__fqn__ != efqn:
            raise Exception(f"Class name '{class_name}' already maps to a different entity class: {curr_eclass}")
        if f2cn and f2cn != class_name:
            raise Exception(f"Entity class {entity_class} is already mapped to {class_name}, Trying to remap to: {f2cn}")
        if not curr_eclass:
            self.name_to_entities[class_name] = entity_class
        if not f2cn:
            self.fqn_to_classname[efqn] = class_name
        return self.fqn_to_classname[efqn]

    def resolve_fqn_or_entity(self, fqn_or_entity):
        entity_class = fqn_or_entity
        if type(fqn_or_entity) is str:
            if fqn_or_entity not in self.fqn_to_entity:
                # resolve it
                resolved, entity_class = resolve_fqn(fqn_or_entity)
                self.fqn_to_entity[fqn_or_entity] = entity_class
        if not issubclass(entity_class, Entity):
            raise(f"{entity_class} is not a class")
        return entity_class

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
            return "http://"
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

    def resolve_generic_arg(self, arg):
        if type(arg) is typing.ForwardRef:
            fqn_or_eclass = arg.__forward_arg__
            result = self.resolve_fqn_or_entity(fqn_or_eclass)
        else:
            result = arg
        return result

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
            return "URL"
        if fields.KeyType in (logical_type.mro()):
            thetype = self.resolve_generic_arg(logical_type.__args__[0])
            return f"Ref<{self.name_for_entity_class(thetype)}>?"
        if logical_type == list:
            return "[Any]"
        if list in (logical_type.mro()):
            thetype = self.resolve_generic_arg(logical_type.__args__[0])
            return f"[{self.swifttype_for(thetype)}]"
        if logical_type == dict:
            return "[String : Any]"
        if dict in logical_type.mro():
            key_type = self.resolve_generic_arg(logical_type.__args__[0])
            val_type = self.resolve_generic_arg(logical_type.__args__[1])
            return f"[{self.swifttype_for(key_type)} : {self.swifttype_for(val_type)}]"
        try:
            if issubclass(logical_type, ModelBase):
                return f"{self.name_for_entity_class(logical_type)}"
        except Exception as exc:
            set_trace()
        assert False, ("Invalid logical_type: ", logical_type)

    def class_for_entity_class(self, entity_class, class_name = None):
        class_name = self.register_entity_class(entity_class, class_name)
        # See if class_name is taken by another entity
        return entity_class_template.render(gen = self,
                    entity_class = entity_class,
                    class_name = class_name)

    def swiftclient_for(self, router, class_name):
        """ Generate the client with method per call in the API router. """
        # See if class_name is taken by another entity
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
