
"""
class TypeContainer(object):
    def __init__(self, fqn, is_named = False):
        self.fqn = fqn
        self.is_named = is_named
        self.children = []

    def clear(self):
        self.children = []
        pass

    def __len__(self):
        return len(self.children)

    def __getitem__(self, index):
        return self.children[index]

    def __iter__(self):
        return iterm(self.children)

class ProductType(TypeContainer):
    pass

class SumType(TypeContainer):
    pass

class TypeFun(TypeContainer):
    pass

class RefType(object):
    def __init__(self, fqn, target_type):
        self.fqn = fqn
        self.target_type = target_type

class Type(Union):
    prod_type = Variant(ProductType)
    sum_type = Variant(SumType)
    ref_type = Variant(RefType)
    type_fun = Variant(TypeFun)
"""

