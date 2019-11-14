
from taggedunion import CaseMatcher, case
import datetime, typing, inspect
import sys
from modelzero.core import custom_fields as fields
from modelzero.core.entities import Entity
from modelzero.core import types
from modelzero.utils import resolve_fqn
from modelzero.gen import core as gencore
import modelzero.apigen.apispec
from ipdb import set_trace

class Generator(gencore.GeneratorBase):
    """ Generates model bindings for model to Swift.  """
    def __init__(self):
        super().__init__()

        # For each logical type we want to create the Kotlin type.   We want to model Kotlin
        # types using our types too since we are essentially looking at type transformation
        # where both the kotlin type, its location (namespace) and structure (fields) may differ
        self.models_by_name = {}
        self.fqn_to_classname = {}
        self.fqn_to_model = {}

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
        assert type(logical_type) is types.Type
        return DefaultValue().valueOf(logical_type)

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

    def converter_call(self, logical_type : types.Type, varvalue):
        if self.is_record_class(logical_type):
            logical_type = types.Type.as_record_type(logical_type)
        if type(logical_type) is not types.Type:
            set_trace()
        return ConverterCall(self).valueOf(logical_type, varvalue)
        
    def kotlintype_for(self, logical_type):
        if self.is_record_class(logical_type):
            logical_type = types.Type.as_record_type(logical_type)
        if type(logical_type) is not types.Type:
            set_trace()
            raise Exception(f"Expecting Type instance, found: {logical_type}")
        """
        if self.is_record_class(logical_type):
            return f"{self.name_for_record_class(logical_type)}"
        if type(logical_type) is not types.Type:
            set_trace()
            raise Exception(f"Expecting Type instance, found: {logical_type}")
        """
        return KotlinTypeEval(self).valueOf(logical_type)

    def class_for_record_class(self, record_class):
        class_name = self.register_record_class(record_class)
        # See if class_name is taken by another model
        return self.load_template("kotlin/record_class").render(gen = self,
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

class KotlinTypeFor(CaseMatcher):
    __caseon__ = types.Type
    def __init__(self, gen):
        self.gen = gen

    def valueOf(self, thetype : types.Type):
        if thetype not in gen.kotlin_types:
            gen.kotlin_types[thetype] = self(thetype)
        return gen.kotlin_types[thetype]

    @case("opaque_type")
    def valueOfOpaqueType(self, thetype : types.OpaqueType):
        if thetype.name == "bool": return "Boolean"
        if thetype.name == "int": return "Int"
        if thetype.name == "long": return "Long"
        if thetype.name == "float": return "Float"
        if thetype.name == "double": return "Double"
        if thetype.name == "bytes": return "Data"
        if thetype.name == "str": return "String"
        if thetype.name == "URL": return "URL"
        if thetype.native_type == typing.Any: return "Any"
        if thetype.native_type == datetime.datetime: return "Date"
        assert False, f"Invald opaque type encountered: {thetype}"

    @case("record_type")
    def valueOfRecordType(self, record_type : types.RecordType):
        record_class = record_type.record_class
        return f"{self.gen.name_for_record_class(record_class)}"

    @case("union_type")
    def valueOfUnionType(self, union_type : types.UnionType):
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
    def valueOfTypeApp(self, type_app : types.TypeApp):
        gen = self.gen
        origin_type = type_app.origin_type
        if not origin_type.is_opaque_type:
            raise Exception("Type application for non-opaque types not yet supported")
        else:
            opaque_type = origin_type.opaque_type
            if opaque_type.native_type == list:
                childtype = type_app.type_args[0]
                return f"List<{self(childtype)}>"
            if opaque_type.native_type == dict:
                key_type = type_app.type_args[0]
                val_type = type_app.type_args[1]
                return f"Map<{self(key_type)}, {self(val_type)}>"
            if opaque_type.name == "Optional":
                optional_of = type_app.type_args[0]
                return f"{self(optional_of)}?"
            if opaque_type.name == "key":
                reftype = type_app.type_args[0]
                if reftype.is_record_type:
                    record_class = reftype.record_class
                elif reftype.is_type_ref:
                    record_class = reftype.target
                else:
                    set_trace()
                    assert False
                return f"Ref<{gen.name_for_record_class(record_class)}>"
        set_trace()
        raise Exception("Invalid type: {type_app}")

class KotlinTypeEval(CaseMatcher):
    __caseon__ = types.Type
    def __init__(self, gen):
        self.gen = gen

    def valueOf(self, thetype : types.Type):
        return self(thetype)

    @case("opaque_type")
    def valueOfOpaqueType(self, thetype : types.OpaqueType):
        if thetype.name == "bool": return "Boolean"
        if thetype.name == "int": return "Int"
        if thetype.name == "long": return "Long"
        if thetype.name == "float": return "Float"
        if thetype.name == "double": return "Double"
        if thetype.name == "bytes": return "Data"
        if thetype.name == "str": return "String"
        if thetype.name == "URL": return "URL"
        if thetype.native_type == typing.Any: return "Any"
        if thetype.native_type == datetime.datetime: return "Date"
        assert False, f"Invald opaque type encountered: {thetype}"

    @case("record_type")
    def valueOfRecordType(self, record_type : types.RecordType):
        record_class = record_type.record_class
        return f"{self.gen.name_for_record_class(record_class)}"

    @case("union_type")
    def valueOfUnionType(self, union_type : types.UnionType):
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
    def valueOfTypeApp(self, type_app : types.TypeApp):
        gen = self.gen
        origin_type = type_app.origin_type
        if not origin_type.is_opaque_type:
            raise Exception("Type application for non-opaque types not yet supported")
        else:
            opaque_type = origin_type.opaque_type
            if opaque_type.native_type == list:
                childtype = type_app.type_args[0]
                return f"List<{self(childtype)}>"
            if opaque_type.native_type == dict:
                key_type = type_app.type_args[0]
                val_type = type_app.type_args[1]
                return f"Map<{self(key_type)}, {self(val_type)}>"
            if opaque_type.name == "Optional":
                optional_of = type_app.type_args[0]
                return f"{self(optional_of)}?"
            if opaque_type.name == "key":
                reftype = type_app.type_args[0]
                if reftype.is_record_type:
                    record_class = reftype.record_class
                elif reftype.is_type_ref:
                    record_class = reftype.target
                else:
                    set_trace()
                    assert False
                return f"Ref<{gen.name_for_record_class(record_class)}>"
        set_trace()
        raise Exception("Invalid type: {type_app}")

class DefaultValue(CaseMatcher):
    """ Returns the native default value for a given type. """
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
        if thetype.name == "URL": return 'URL("http://")'
        if thetype.native_type == typing.Any: return "null"
        if thetype.native_type == datetime.datetime: return "Date()"
        assert False, f"Invald opaque type encountered: {thetype}"

    @case("record_type")
    def valueOfRecordType(self, thetype : types.RecordType):
        set_trace()

    @case("union_type")
    def valueOfUnionType(self, union_type : types.UnionType):
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

class ConverterCall(CaseMatcher):
    __caseon__ = types.Type
    def __init__(self, gen):
        self.gen = gen

    def valueOf(self, thetype : types.Type, varvalue):
        return self(thetype, varvalue)

    @case("opaque_type")
    def valueOfOpaqueType(self, thetype : types.OpaqueType, varvalue):
        if thetype.name == "bool": return f"boolFromAny({varvalue}!!)"
        if thetype.name == "int": return f"intFromAny({varvalue}!!)"
        if thetype.name == "long": return f"longFromAny({varvalue}!!)"
        if thetype.name == "float": return f"floatFromAny({varvalue}!!)"
        if thetype.name == "double": return f"doubleFromAny({varvalue}!!)"
        if thetype.name == "str": return f"stringFromAny({varvalue}!!)"
        if thetype.name == "URL": return f"urlFromAny({varvalue}!!)"
        if thetype.name == "bytes": return f"bytesFromAny({varvalue}!!)"
        if thetype.native_type == datetime.datetime: return f"dateFromAny({varvalue}!!)"
        if thetype.native_type == typing.Any: return "Any"
        assert False, f"Invald opaque type encountered: {thetype}"

    @case("record_type")
    def valueOfRecordType(self, record_type : types.RecordType, varvalue):
        record_class = record_type.record_class
        return f"{self.gen.name_for_record_class(record_class)}({varvalue} as DataMap)"

    @case("union_type")
    def valueOfUnionType(self, thetype : types.UnionType, varvalue):
        set_trace()

    @case("sum_type")
    def valueOfSumType(self, thetype : types.SumType, varvalue):
        set_trace()

    @case("type_var")
    def valueOfTypeVar(self, thetype : types.TypeVar, varvalue):
        set_trace()

    @case("type_ref")
    def valueOfTypeRef(self, thetype : types.TypeRef, varvalue):
        set_trace()

    @case("type_app")
    def valueOfTypeApp(self, type_app : types.TypeApp, varvalue):
        # TODO - need to make this passable too
        # if logical_type == list: return "[Any]"
        # if logical_type == dict: return "[String : Any]"
        gen = self.gen
        origin_type = type_app.origin_type
        if not origin_type.is_opaque_type:
            raise Exception("Type application for non-opaque types not yet supported")
        else:
            opaque_type = origin_type.opaque_type
            if opaque_type.native_type == list:
                childtype = type_app.type_args[0]
                return f"""({varvalue} as List<Any>).map {{
                    {gen.converter_call(childtype, "it")}
                }}
                """
            if opaque_type.native_type == dict:
                key_type = type_app.type_args[0]
                val_type = type_app.type_args[1]
                return f"Map<{gen.kotlintype_for(key_type)}, {gen.kotlintype_for(val_type)}>"
            if opaque_type.name == "Optional":
                optional_of = type_app.type_args[0]
                return gen.converter_call(optional_of, varvalue)
            if opaque_type.name == "key":
                reftype = type_app.type_args[0]
                if reftype.is_record_type:
                    record_class = reftype.record_class
                elif reftype.is_type_ref:
                    record_class = reftype.target
                else:
                    set_trace()
                    assert False
                return f"refFromAny<{gen.name_for_record_class(record_class)}>({varvalue}!!)"
        set_trace()
        raise Exception("Invalid type: {type_app}")
