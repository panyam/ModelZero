
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
    def __init__(self, target_models_package):
        super().__init__()
        self.target_models_package = target_models_package

        # For each logical type we want to create the Kotlin type.   We want to model Kotlin
        # types using our types too since we are essentially looking at type transformation
        # where both the kotlin type, its location (namespace) and structure (fields) may differ
        self.kotlin_types = {}

    def ensure_kotlin_type(self, fqn):
        newcreated = fqn not in self.kotlin_types
        if newcreated:
            self.kotlin_types[fqn] = types.Type()
        return self.kotlin_types[fqn], newcreated

    def default_value_for(self, logical_type):
        assert type(logical_type) is types.Type
        return DefaultValue().valueOf(logical_type)

    def converter_call(self, logical_type : types.Type, varvalue):
        if self.is_record_class(logical_type):
            logical_type = types.Type.as_record_type(logical_type)
        if type(logical_type) is not types.Type:
            set_trace()
        return ConverterCall(self)(logical_type, varvalue)
        
    def kotlin_type_for(self, logical_type):
        """ Returns the transformed kotlin type for a given logical type. """
        return KotlinTypeFor(self)(logical_type)

    def kotlin_sig_for(self, logical_type):
        if self.is_record_class(logical_type):
            logical_type = types.Type.as_record_type(logical_type)
        if type(logical_type) is not types.Type:
            set_trace()
            raise Exception(f"Expecting Type instance, found: {logical_type}")
        return KotlinTypeSig(self)(logical_type)

    def class_for_record_class(self, record_class):
        # See if class_name is taken by another model
        return self.load_template("kotlin/record_class").render(gen = self,
                    record_class = record_class.record_type.record_class)

    def kotlinclient_for(self, router, class_name, url_prefix):
        """ Generate the client with method per call in the API router. """
        # See if class_name is taken by another model
        from collections import deque
        out = [f"class {class_name}(httpClient : HttpClient) : JBClient(httpClient) {{"]
        def visit(r, path = ""):
            for httpmethod,method in r.methods.items():
                out.append(self.func_for_router_method(httpmethod, method, path))

            for prefix,child in r.children:
                visit(child, path + prefix)
        visit(router, url_prefix)
        out.append("}")
        return "\n".join(out)

    def func_for_router_method(self, http_method, method, prefix):
        path_prefix = prefix
        for name, param in method.patharg_params.items():
            path_prefix = path_prefix.replace(f"{{{name}}}", f"${name}")

        return_type = self.kotlin_type_for(method.return_type)
        param_types = {n: self.kotlin_type_for(pt) for n,pt in method.param_types.items()}
        return self.load_template("kotlin/api_method").render(method = method,
                                          http_method = http_method,
                                          path_prefix = path_prefix,
                                          param_types = param_types,
                                          return_type = return_type,
                                          gen = self)

class KotlinTypeFor(CaseMatcher):
    __caseon__ = types.Type
    def __init__(self, gen):
        self.gen = gen

    @case("opaque_type")
    def kTypeForOpaqueType(self, thetype : types.OpaqueType):
        t = None
        gen = self.gen
        if thetype.name == "bool":
            t,nc = gen.ensure_kotlin_type("Boolean")
            if nc: t.opaque_type = types.OpaqueType("Boolean")
        if thetype.name == "int":
            t,nc = gen.ensure_kotlin_type("Int")
            if nc: t.opaque_type = types.OpaqueType("Int")
        if thetype.name == "long":
            t,nc = gen.ensure_kotlin_type("Long")
            if nc: t.opaque_type = types.OpaqueType("Long")
        if thetype.name == "float":
            t,nc = gen.ensure_kotlin_type("Float")
            if nc: t.opaque_type = types.OpaqueType("Float")
        if thetype.name == "double":
            t,nc = gen.ensure_kotlin_type("Double")
            if nc: t.opaque_type = types.OpaqueType("Double")
        if thetype.name == "str":
            t,nc = gen.ensure_kotlin_type("String")
            if nc: t.opaque_type = types.OpaqueType("String")
        if thetype.name == "bytes":
            t,nc = gen.ensure_kotlin_type("Data")
            if nc: t.opaque_type = types.OpaqueType("Data")
        if thetype.name == "URL":
            t,nc = gen.ensure_kotlin_type("URL")
            if nc: t.opaque_type = types.OpaqueType("URL")
        if thetype.native_type == typing.Any:
            t,nc = gen.ensure_kotlin_type("Any")
            if nc: t.opaque_type = types.OpaqueType("Any")
        if thetype.native_type == datetime.datetime:
            t,nc = gen.ensure_kotlin_type("Date")
            if nc: t.opaque_type = types.OpaqueType("Date")
        if thetype.name == "list":
            t,nc = gen.ensure_kotlin_type("List")
            if nc: t.opaque_type = types.OpaqueType("List")
        if thetype.name == "map":
            t,nc = gen.ensure_kotlin_type("Map")
            if nc: t.opaque_type = types.OpaqueType("Map")
        if thetype.name == "key":
            t,nc = gen.ensure_kotlin_type("Ref")
            if nc: t.opaque_type = types.OpaqueType("Ref")
        if thetype.name == "Optional":
            t,nc = gen.ensure_kotlin_type("Optional")
            if nc: t.opaque_type = types.OpaqueType("Optional")
        if t is None:
            set_trace()
            raise Exception(f"Invalid opaque type encountered: {thetype.name}")
        return t

    @case("record_type")
    def kTypeForRecordType(self, record_type : types.RecordType):
        gen = self.gen
        record_class = record_type.record_class
        # TODO - should name be the same?
        new_name = record_class.__fqn__.split(".")[-1]
        new_fqn = f"{gen.target_models_package}.{new_name}"
        t,nc = gen.ensure_kotlin_type(new_fqn)
        if nc:
            class_dict = dict(SourceRecordClass = record_class,
                              __module__ = gen.target_models_package,
                              __fqn__ = new_fqn)
            new_record_class = type(new_name,
                                    (types.Record,),
                                    class_dict)
            t.record_type = types.RecordType(new_record_class)
            for name,field in record_class.__record_fields__.items():
                newfield = field.clone()
                newfield.base_type = self(field.base_type)
                new_record_class.register_field(name, newfield)
        return t

    @case("union_type")
    def kTypeForUnionType(self, union_type : types.UnionType):
        set_trace()

    @case("sum_type")
    def kTypeForSumType(self, thetype : types.SumType):
        set_trace()

    @case("type_var")
    def kTypeForTypeVar(self, thetype : types.TypeVar):
        set_trace()

    @case("type_ref")
    def kTypeForTypeRef(self, thetype : types.TypeRef):
        target = thetype.target
        if not hasattr(target, "SourceRecordClass"):
            # Then it is possible this class has not yet been "reached"
            # So kick off its 
            return self.kTypeForRecordType(types.RecordType(target))
        else:
            return Type.as_record_type(types.RecordType(target))

    @case("type_app")
    def kTypeForTypeApp(self, type_app : types.TypeApp):
        gen = self.gen
        origin_type = type_app.origin_type
        new_origin_type = self(origin_type)
        new_type_args = [self(a) for a in type_app.type_args]
        result = new_origin_type.__getitem__(*new_type_args)
        if result.origin_type.name == "Ref":
            if result.type_args[0].is_type_app:
                set_trace()
        return result

class KotlinTypeSig(CaseMatcher):
    __caseon__ = types.Type
    def __init__(self, gen):
        self.gen = gen

    @case("opaque_type")
    def sigForOpaqueType(self, thetype : types.OpaqueType):
        return thetype.name

    @case("record_type")
    def sigForRecordType(self, record_type : types.RecordType):
        record_class = record_type.record_class
        return f"{record_class.__fqn__}"

    @case("union_type")
    def sigForUnionType(self, union_type : types.UnionType):
        set_trace()

    @case("sum_type")
    def sigForSumType(self, thetype : types.SumType):
        set_trace()

    @case("type_var")
    def sigForTypeVar(self, thetype : types.TypeVar):
        set_trace()

    @case("type_ref")
    def sigForTypeRef(self, thetype : types.TypeRef):
        set_trace()

    @case("type_app")
    def sigForTypeApp(self, type_app : types.TypeApp):
        gen = self.gen
        origin_type = type_app.origin_type
        if not origin_type.is_opaque_type:
            raise Exception("Type application for non-opaque types not yet supported")
        else:
            opaque_type = origin_type.opaque_type
            if opaque_type.name == "Optional":
                optional_of = type_app.type_args[0]
                return f"{self(optional_of)}?"
            child_type_sigs = map(self, type_app.type_args)
            return f"""{self(origin_type)}<{", ".join(child_type_sigs)}>"""
        raise Exception("Invalid type: {type_app}")

class DefaultValue(CaseMatcher):
    """ Returns the native default value for a given type. """
    __caseon__ = types.Type

    def defValFor(self, thetype : types.Type):
        return self(thetype)

    @case("opaque_type")
    def defValForOpaqueType(self, thetype : types.OpaqueType):
        if thetype.name == "bool": return "false"
        if thetype.name in ("int", "long"): return "0"
        if thetype.name in ("float", "double"): return "0"
        if thetype.name == "bytes": return "null"
        if thetype.name == "str": return '""'
        if thetype.name == "URL": return 'URL("http://")'
        if thetype.native_type == typing.Any: return "null"
        if thetype.native_type == datetime.datetime: return "Date()"
        assert False, f"Invalid opaque type encountered: {thetype}"

    @case("record_type")
    def defValForRecordType(self, thetype : types.RecordType):
        set_trace()

    @case("union_type")
    def defValForUnionType(self, union_type : types.UnionType):
        set_trace()

    @case("sum_type")
    def defValForSumType(self, thetype : types.SumType):
        set_trace()

    @case("type_var")
    def defValForTypeVar(self, thetype : types.TypeVar):
        set_trace()

    @case("type_ref")
    def defValForTypeRef(self, thetype : types.TypeRef):
        set_trace()

    @case("type_app")
    def defValForTypeApp(self, thetype : types.TypeApp):
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

    @case("opaque_type")
    def callForOpaqueType(self, thetype : types.OpaqueType, varvalue):
        if thetype.name == "Any": return f"{varvalue}!!"
        if thetype.name in ("Boolean", "Int", "Long", "Float", "Double", "String", "URL", "Data", "Date"):
            return f"{thetype.name.lower()}FromAny({varvalue}!!)"
        set_trace()
        assert False, f"Invalid opaque type encountered: {thetype.name}"

    @case("record_type")
    def callForRecordType(self, record_type : types.RecordType, varvalue):
        record_class = record_type.record_class
        return f"{record_class.__fqn__}({varvalue})"

    @case("union_type")
    def callForUnionType(self, thetype : types.UnionType, varvalue):
        set_trace()

    @case("sum_type")
    def callForSumType(self, thetype : types.SumType, varvalue):
        set_trace()

    @case("type_var")
    def callForTypeVar(self, thetype : types.TypeVar, varvalue):
        set_trace()

    @case("type_ref")
    def callForTypeRef(self, thetype : types.TypeRef, varvalue):
        set_trace()

    @case("type_app")
    def callForTypeApp(self, type_app : types.TypeApp, varvalue):
        # TODO - need to make this passable too
        # if logical_type == list: return "[Any]"
        # if logical_type == dict: return "[String : Any]"
        gen = self.gen
        origin_type = type_app.origin_type
        if not origin_type.is_opaque_type:
            set_trace()
            raise Exception("Type application for non-opaque types not yet supported")
        else:
            opaque_type = origin_type.opaque_type
            if opaque_type.name == "List":
                childtype = type_app.type_args[0]
                return f"""{varvalue}.map {{
                    {gen.converter_call(childtype, "it")}
                }}.collect(Collectors.toList())"""
            if opaque_type.name == "Map":
                key_type = type_app.type_args[0]
                val_type = type_app.type_args[1]
                return f"Map<{gen.kotlin_sig_for(key_type)}, {gen.kotlin_sig_for(val_type)}>"
            if opaque_type.name == "Optional":
                optional_of = type_app.type_args[0]
                return gen.converter_call(optional_of, varvalue)
            if opaque_type.name == "Ref":
                reftype = type_app.type_args[0]
                if reftype.is_record_type:
                    record_class = reftype.record_class
                elif reftype.is_type_ref:
                    record_class = reftype.target
                else:
                    set_trace()
                    assert False
                return f"refFromAny<{record_class.__fqn__}>({varvalue}!!)"
        set_trace()
        raise Exception("Invalid type: {type_app}")
