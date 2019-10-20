
import sys
from modelzero.core import fields
from modelzero.core.models import ModelBase
from ipdb import set_trace

class Generator(object):
    def __init__(self):
        self.registry = {}
        # Swift does not have packages
        self.name_to_entity_mapping = {}
        self.target_entity_info = {}

    def name_for_entity_class(self, entity_class):
        fqn = entity_class.__fqn__
        name = entity_class.__name__
        return name

    def code_for_entity_class(self, entity_class):
        result = self.class_for_entity_class(entity_class)
        return result

    def class_for_entity_class(self, entity_class):
        out = []
        proto_name = entity_class.__name__
        class_name = f"{proto_name}"
        out.append(f"class {class_name} : AbstractEntity {{")
        for name, field in entity_class.__model_fields__.items():
            out.append(f"    var {name} : {self.swift_type_for_field(field)} = {self.default_value_for_field(field)}")
        out.append("}")
        return "\n".join(out)

    def default_value_for_field(self, field):
        if isinstance(field, fields.BooleanField):
            return "false"
        elif isinstance(field, fields.IntegerField):
            return "0"
        elif isinstance(field, fields.LongField):
            return "0"
        elif isinstance(field, fields.JsonField):
            return "nil"
        elif isinstance(field, fields.AnyField):
            return "nil"
        elif isinstance(field, fields.FloatField):
            return "0"
        elif isinstance(field, fields.BytesField):
            return "nil"
        elif isinstance(field, fields.StringField):
            return '""'
        elif isinstance(field, fields.DateTimeField):
            return "Date(timeIntervalSince1970: 0)"
        elif isinstance(field, fields.KeyField):
            return "nil"
        elif isinstance(field, fields.URLField):
            return "http://"
        elif isinstance(field, fields.ListField):
            return "[]"
        elif isinstance(field, fields.MapField):
            return "nil"
        assert False, f"Invalid field found: {field}"

    def swift_type_for_field(self, field):
        if isinstance(field, fields.BooleanField):
            return "Bool"
        elif isinstance(field, fields.IntegerField):
            return "Int"
        elif isinstance(field, fields.LongField):
            return "Long"
        elif isinstance(field, fields.JsonField):
            return "Any?"
        elif isinstance(field, fields.AnyField):
            return "Any?"
        elif isinstance(field, fields.FloatField):
            return "Float"
        elif isinstance(field, fields.BytesField):
            return "Data?"
        elif isinstance(field, fields.StringField):
            return "String"
        elif isinstance(field, fields.URLField):
            return "URL"
        elif isinstance(field, fields.DateTimeField):
            return "Date"
        elif isinstance(field, fields.KeyField):
            field.resolve()
            return f"Ref<{self.name_for_entity_class(field.entity_class)}>?"
            # return "Ref?"
        elif isinstance(field, fields.ListField):
            field.resolve()
            if isinstance(field.child_type, fields.Field):
                return f"[{self.swift_type_for_field(field.child_type)}]"
            else:
                assert issubclass(field.child_type, ModelBase)
                return f"[{self.name_for_entity_class(field.child_type)}]"
        elif isinstance(field, fields.MapField):
            field.resolve()
            out = "["

            if isinstance(field.key_type, fields.Field):
                out += f"{self.swift_type_for_field(field.key_type)}"
            else:
                assert issubclass(field.key_type, ModelBase)
                out += f"{self.name_for_entity_class(field.key_type)}"
            out += " : "

            if isinstance(field.value_type, fields.Field):
                out += f"{self.swift_type_for_field(field.value_type)}"
            else:
                assert issubclass(field.value_type, ModelBase)
                out += f"{self.name_for_entity_class(field.value_type)}"
            out += " ]?"
            return out
        assert False, ("Invalid field type: ", field)

def generate_entity(entity_class, outstream = sys.stdout):
    """ Generate an entity to a given output stream with swift bindings. """
    outstream.write(f"struct {entity_class.__name__} : Hashable, Codable " + "{")
    for name, field in entity_class.__model_fields__.items():
        outstream.write(f"    var {name} : {swift_type_for_field(field)} \n")
    outstream.write("}")
