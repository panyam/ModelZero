
from ipdb import set_trace
from typing import List, Dict
from taggedunion import Union, Variant
from modelzero.core.records import Record

def ensure_type(type_or_str):
    if type(type_or_str) is str:
        type_or_str = Type.as_type_ref(type_or_str)
    elif type(type_or_str) is not Type:
        if issubclass(type_or_str, Record):
            type_or_str = Type.as_record_type(type_or_str)
        else:
            set_trace()
            raise Exception(f"Expected type or string, found: {type_or_str}")
    return type_or_str

class TypeApp(object): 
    def __init__(self, origin_type : "Type", *args : List["Type"]):
        self.origin_type = origin_type
        self.type_args = [ensure_type(a) for a in args]

class TypeRef(object):
    def __init__(self, target_fqn : str):
        self.target_fqn = target_fqn
        self._target = None

    @property
    def target(self):
        if self._target is None:
            from modelzero.utils import resolve_fqn
            resolved, self._target = resolve_fqn(self.target_fqn)
            assert resolved
        return self._target

class TypeVar(object):
    def __init__(self, name : str):
        self.varname = name

class DataType(object):
    def __init__(self, name : str = None):
        self._name = name
        self._children = []

    @property
    def name(self): return self._name

    @property
    def childcount(self): return len(self._children)

    def type_at(self, index): return self._children[index]

    def add(self, *children : List["Type"]):
        for child in children:
            self._children.append(ensure_type(child))
        return self

class OpaqueType(object):
    def __init__(self, name : str, native_type = None):
        self._name = name
        self._native_type = native_type

    @property
    def name(self): return self._name

    @property
    def native_type(self): return self._native_type

class RecordType(object):
    def __init__(self, record_class_or_fqn):
        if type(record_class_or_fqn) is str:
            self._record_fqn = record_class_or_fqn
            self._record_class = None
        elif issubclass(record_class_or_fqn, Record):
            self._record_fqn = record_class_or_fqn.__fqn__
            self._record_class = record_class_or_fqn
        else:
            raise Exception(f"Found {record_class_or_fqn}, Expected str or 'Record' class")

    @property
    def record_class(self):
        if self._record_class is None:
            resolved, self._record_class = resolve_fqn(self._record_fqn)
            assert resolved
        return self._record_class

class UnionType(object):
    def __init__(self, union_class_or_fqn):
        if type(union_class_or_fqn) is str:
            self._union_fqn = union_class_or_fqn
            self._union_class = None
        elif issubclass(union_class_or_fqns, Union):
            self._union_fqn = union_class_or_fqn.__fqn__
            self._union_class = union_class_or_fqn
        else:
            raise Exception(f"Found {union_class_or_fqn}, Expected str or 'Union' class")

    @property
    def union_class(self):
        if self._union_class is None:
            resolved, self._union_class = resolve_fqn(self._union_fqn)
            assert resolved
        return self._union_class

class SumType(DataType): pass

class Type(Union):
    record_type = Variant(RecordType)
    union_type = Variant(UnionType)
    sum_type = Variant(SumType)
    opaque_type = Variant(OpaqueType)
    type_app = Variant(TypeApp)
    type_var = Variant(TypeVar)
    type_ref = Variant(TypeRef)

    def __getitem__(self, *keys):
        return Type.as_type_app(self, *keys)

