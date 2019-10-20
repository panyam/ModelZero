
import sys
from modelzero.core import fields
from ipdb import set_trace

class SwiftGenerator(object):
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
        return "\n\n".join([self.protocol_for_entity_class(entity_class), self.class_for_entity_class(entity_class)])

    def protocol_for_entity_class(self, entity_class):
        out = []
        # Todo check that duplicate entities are named properly
        # so that the lack of namespaces wont allow collissions
        # to happen
        out.append(f"protocol {entity_class.__name__} : Entity {{")
        for name, field in entity_class.__model_fields__.items():
            out.append(f"    var {name} : {self.swift_type_for_field(field)} {{ get set }}")
        out.append("}")
        return "\n".join(out)

    def class_for_entity_class(self, entity_class):
        out = []
        proto_name = entity_class.__name__
        class_name = f"Default{proto_name}"
        out.append(f"class {class_name} : AbstractEntity, {proto_name} {{")
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
            field.resolve()
            return "nil"
        assert False, "Invalid field found"

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
        elif isinstance(field, fields.DateTimeField):
            return "Date"
        elif isinstance(field, fields.KeyField):
            field.resolve()
            return f"Ref<{self.name_for_entity_class(field.entity_class)}>?"
        assert False, ("Invalid field type: ", field)

def generate_entity(entity_class, outstream = sys.stdout):
    """ Generate an entity to a given output stream with swift bindings. """
    outstream.write(f"struct {entity_class.__name__} : Hashable, Codable " + "{")
    for name, field in entity_class.__model_fields__.items():
        outstream.write(f"    var {name} : {swift_type_for_field(field)} \n")
    outstream.write("}")
