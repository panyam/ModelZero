
from ipdb import set_trace
from typing import List, Dict
from taggedunion import Union, Variant

def ensure_type(type_or_str):
    if type(type_or_str) is str:
        type_or_str = Type.as_type_ref(type_or_str)
    return type_or_str

class TypeRef(object):
    def __init__(self, target_fqn : str):
        self.target_fqn = target_fqn

class TypeVar(object):
    def __init__(self, name : str):
        self.varname = name

class DataType(object):
    def __init__(self, name : str = None, tagged : bool = False):
        self._name = name
        self._tagged = tagged
        self._tags = []
        self._children = []

    @property
    def name(self): return self._name

    @property
    def childcount(self): return len(self._children)

    @property
    def is_tagged(self): return self._tagged 

    def type_at(self, index): return self._children[index]

    def tag_at(self, index): return self._tags[index]

    def type_for_tag(self, tag):
        if not self.is_tagged:
            raise Exception("Data type is not tagged")
        for childtag,T in zip(self._tags, self._children):
            if tag == childtag: return T
        return None

    def add(self, *children : List["Type"], **tagged_children: Dict[str, "Type"]):
        if self.is_tagged:
            if children or not tagged_children:
                raise Exception("Tagged data types must ONLY specify tagged_children parameter")
            for child in children:
                self._children.append(ensure_type(child))
        else:
            if tagged_children or not children:
                raise Exception("Untagged data types must ONLY specify children parameter")
                for tag, child in tagged_children.items():
                    if tag in self._tags:
                        raise Exception(f"Tag {tag} already exists.")
                    self._tags.append(child)
                    self._children.append(ensure_type(child))
        return self

class ProductType(DataType): pass
class SumType(DataType): pass

class OpaqueType(DataType):
    def __init__(self, name : str, native_type = None):
        super().__init__(name = name)
        self._native_type = native_type

    @property
    def native_type(self): return self._native_type

    def add(self, *args, **kwargs):
        # TODO: Is this always true?
        raise Exception("Children cannot be added to Opaque/Native types")

class TypeApp(object): 
    def __init__(self, origin_type : "Type", *args : List["Type"]):
        self.origin_type = origin_type
        self.type_args = [ensure_type(a) for a in args]

class Type(Union):
    prod_type = Variant(ProductType)
    sum_type = Variant(SumType)
    opaque_type = Variant(OpaqueType)
    type_app = Variant(TypeApp)
    type_var = Variant(TypeVar)
    type_ref = Variant(TypeRef)

    def __getitem__(self, *keys):
        return Type.as_type_app(self, *keys)
