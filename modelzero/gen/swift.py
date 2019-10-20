
import sys
from modelzero.core import fields
from modelzero.core.models import ModelBase
from ipdb import set_trace

class Generator(object):
    """ Generates model bindings for entities to Swift.  """
    def __init__(self):
        # Swift does not have packages so we need names to be unique
        # and this uniqueness can come by not ensuring two classes globally 
        # dont have the same name *or* letting user specify an alternative name
        # for an entity
        self.name_to_entities = {}
        self.entity_infos = {}

    def name_for_entity_class(self, entity_class):
        return self.register_entity_class(entity_class)
        efqn = entity_class.__fqn__
        if efqn not in self.entity_infos:
            raise KeyError(f"{entity_class}")
        einfo = self.entity_infos.get(efqn)
        return einfo['class_name']

    def register_entity_class(self, entity_class, class_name = None):
        efqn = entity_class.__fqn__
        einfo = self.entity_infos.get(efqn, None)
        class_name = class_name or entity_class.__name__
        curr_eclass = self.name_to_entities.get(class_name, None)
        if curr_eclass and self.name_to_entities[class_name].__fqn__ != efqn:
            raise Exception(f"Class name '{class_name}' already maps to a different entity class: {curr_eclass}")
        if einfo and einfo["class_name"] != class_name:
            raise Exception(f"Entity class {entity_class} is already mapped to {class_name}")
        if not curr_eclass:
            self.name_to_entities[class_name] = entity_class
        if not einfo:
            einfo = self.entity_infos[efqn] = {'class_name': class_name, 'entity_class': entity_class}
        return einfo['class_name']

    def class_for_entity_class(self, entity_class, class_name = None):
        class_name = self.register_entity_class(entity_class, class_name)
        # See if class_name is taken by another entity
        out = []
        out.append(f"class {class_name} : AbstractEntity {{")
        for name, field in entity_class.__model_fields__.items():
            out.append(f"    var {name} : {self.swift_type_for_field(field)} = {self.default_value_for_field(field)}")

        """
        # Generate ID methods
        kfs = entity_class.key_fields()
        if not kfs:
            out.append("    var id : ID?")
        else:
            kfs = [f"{{{kf}}}" for kf in kfs]
            out.append("    var id : ID {")
            out.append("    }")
        """
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

