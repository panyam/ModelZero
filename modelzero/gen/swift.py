
import datetime, typing
import sys
from modelzero.core import custom_fields as fields
from modelzero.core.models import ModelBase
from modelzero.core.entities import Entity
from modelzero.utils import resolve_fqn
from ipdb import set_trace

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

    def default_value_for_type(self, logical_type):
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
        if list in (logical_type.mro()):
            thetype = self.resolve_generic_arg(logical_type.__args__[0])
            return f"[{self.swifttype_for(thetype)}]"
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
        out = []
        out.append(f"class {class_name} : AbstractEntity {{")
        for name, field in entity_class.__model_fields__.items():
            out.append(f"    var {name} : {self.swifttype_for(field.logical_type)} = {self.default_value_for_type(field.logical_type)}")

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
        return out

    def swiftclient_for(self, router, class_name):
        # See if class_name is taken by another entity
        from collections import deque
        out = []
        out.append(f"class {class_name} {{")

        queue = deque([router])
        while queue:
            next = queue.pop()
            # Add children
            for name,child in next.children:
                queue.appendleft(child)

            for name,method in next.methods.items():
                out.extend(self.func_for_router_method(method))
        out.append("}")
        return out

    def func_for_router_method(self, method):
        out = []
        import inspect
        from inspect import signature
        target_method = method.method
        sig = signature(target_method)
        for name,param in sig.parameters.items():
            if name != "self":
                set_trace()
        # create the method here
        # def param_sig(param): return "let {name}, {swift_type_for_field(kJ
        out.append(f"""func {method.name}() -> AsyncResultState<[<generate return type]> {{
        """)
        out.append(f"    }}")
        return out


"""
How do we descrbe routers and apis and clients?

We ahve a few ways:
    1. Specify an "interface spec" that describes the service is along with function name, 
       param names and types, return type (and name if lang supports it).  From this we can generate 
       the service stub that needs to be "implemented" by the service owner.  This is similar to
       our "engine" methods.
    2. Start with the engine methods.  Inspect its type signature, doc strings etc and infer
        the "interface spec", each time the engine method changes, the spec automatically 
        gets updated (via our generator).

In both cases we have pros and cons.

In the first case - having a single interface DSL, is pretty much what protobufs, thrift, restli gives us.
There is no reason we couldnt use these instead of coming up with a new DSL (sure it is still a python spec
but this is pretty much a DSL as we are describing a service and letting code gen setup the service stubs etc).

The second case is pretty interesting.   Our docgen tools, inspection tools already give us info about what is
returned, accepted params etc are.  If we are ok with programming our services in python (leave perf alone for now) 
then why have a different DSL describing our service intent when the implementation can be it?

The other thing here is if we went with a DSL approach then we are locking down to the "limitations" of a DSL
whether it is expressing types or service details etc.  However with a "start" with language approach
we have the flexibility of adapting the generator as we see fit.

The only caveat is if we cannot "inspect" from the function.  But if this was the case we could always embed a DSL 
in the doc strings which still localizes the intent close to where we want to implement.
"""

