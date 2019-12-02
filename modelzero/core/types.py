
from ipdb import set_trace
import typing
from typing import List, Dict, Tuple
from taggedunion import Union, Variant

class FieldPath(object):
    def __init__(self, value : typing.Union[str, typing.List[str]]):
        if type(value) is str:
            value = [v.strip() for v in value.split("/") if v.strip()]
        self.parts = value

    def __getitem__(self, index):
        return self.parts[index]

def ensure_type(type_or_str):
    if type(type_or_str) is str:
        type_or_str = Type.as_type_ref(type_or_str)
    elif type(type_or_str) is not Type:
        from modelzero.core.records import Record
        if issubclass(type_or_str, Record):
            type_or_str = Type.as_record_type(type_or_str)
        else:
            set_trace()
            raise Exception(f"Expected type or string, found: {type_or_str}")
    return type_or_str

class FuncType(object):
    def __init__(self, param_types : Dict[str, "Type"],
                       return_type : "Type"):
        self.param_types = param_types
        self.return_type = return_type

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
    def children(self): return iter(self._children)

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
        from modelzero.core.records import Record
        if type(record_class_or_fqn) is str:
            self._record_fqn = record_class_or_fqn
            self._record_class = None
        elif issubclass(record_class_or_fqn, Record):
            self._record_fqn = record_class_or_fqn.__fqn__
            self._record_class = record_class_or_fqn
        else:
            raise Exception(f"Found {record_class_or_fqn}, Expected str or 'Record' class")

    def type_for_key(self, key):
        field = self.record_class.__record_metadata__[key]
        return field.logical_type

    @classmethod
    def new_record_class(cls, name, **class_dict):
        from modelzero.core.records import Record
        return type(name, (Record,), class_dict)

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

    def type_for_key(self, key):
        set_trace()
        return None

    @property
    def union_class(self):
        if self._union_class is None:
            resolved, self._union_class = resolve_fqn(self._union_fqn)
            assert resolved
        return self._union_class

class SumType(DataType):
    def __init__(self, name : str = None, *variants : List["Type"]):
        super().__init__(name)
        for v in variants:
            self.add(v)

    def child_if_exists_in_all_variants(self, name):
        candidates = []
        queue = list(self.children)
        while queue:
            ch = queue.pop()
            if ch.is_record_type:
                rmeta = ch.record_class.__record_metadata__
                if name not in rmeta: return None
                candidates.append(rmeta[name].logical_type)
            elif ch.is_union_type:
                vt = ch.union_class.hasvariant(name)
                if vt is None: return None
                candidates.append(vt)
            elif ch.is_sum_type:
                # add 
                for ch in ch.sum_type.children:
                    queue.append(ch)
            else:   # We have non collection types so this cannot be shared field
                return None
        L = len(candidates)
        if L == 1: return candidates[0]
        child_type = candidates[0]
        for cand in candidates[1:]:
            if cand != child_type: return None
        return child_type

class ProductType(DataType):
    def __init__(self, name : str = None, *variants : List["Type"]):
        super().__init__(name)
        for v in variants:
            self.add(v)

class Type(Union):
    record_type = Variant(RecordType)
    union_type = Variant(UnionType)
    sum_type = Variant(SumType)
    product_type = Variant(ProductType)
    opaque_type = Variant(OpaqueType)
    type_app = Variant(TypeApp)
    type_var = Variant(TypeVar)
    type_ref = Variant(TypeRef)
    func_type = Variant(FuncType)

    def __getitem__(self, *keys):
        return Type.as_type_app(self, *keys)

    def type_for_field_path(self, *parts):
        curr = self
        for p in parts:
            if type(p) is int:
                assert curr.is_sum_type or curr.is_product_type
                curr = curr.type_at(p)
            elif type(p) is str:
                if curr.is_sum_type:
                    # This is an interesting case, we will go deeper here
                    # if "p" exists in "all" the variants of 'curr'
                    curr = curr.sum_type.child_if_exists_in_all_variants(p)
                    if curr is None:
                        raise Exception(f"Part '{p}' has different types across sum type")
                elif not curr.is_record_type and not curr.is_union_type:
                    set_trace()
                    assert False
                else:
                    curr = curr.type_for_key(p)
            else:
                set_trace()
                raise Exception("Type being indexed can only be sum, product, record or union types")
        return curr

    def __call__(self, variant, *args, **kwargs):
        set_trace()
        pass

    def get_child_type(self, name):
        if self.is_record_type:
            return self.record_class.__record_metadata__[name].logical_type
        elif self.is_union_type: 
            return self.union_class.get_variant_type(name)
        elif self.is_sum_type:
            self.sum_type.child_if_exists_in_all_variants(name)
        return None
