
from ipdb import set_trace

class IEnv(object):
    """ An environment provides mappings between a variable and its values. """
    def __init__(self, parent = None):
        self.parent = parent

    def get(self, var):
        """ Applies a given function on a variable within this environment. """
        pass

    def push(self):
        """ Create a new environment by extending this one with new variable bindings. """
        return self.__class__(self)

    def extend(self, **var_and_values):
        """ Create a new environment by extending this one with new variable bindings. """
        return self.push().set(**var_and_values)

    def set(self, **kvs):
        for k,v in kvs.items():
            self.setone(k,v)
        return self

class Ref(object):
    def __init__(self, value):
        self.value = value

class DefaultEnv(IEnv):
    """ A default environment. """
    def __init__(self, parent = None, **values):
        IEnv.__init__(self, parent)
        self.refs = {k:Ref(v) for k,v in values.items()}

    def getref(self, var):
        if type(var) is not str: set_trace()
        if var in self.refs: return self.refs[var]
        elif self.parent: return self.parent.getref(var)
        else: return None

    def get(self, var):
        ref = self.getref(var)
        if not ref:
            set_trace()
            raise Exception("Unresolved symbol: %s" % var)
        return ref.value

    def replace(self, key, value):
        ref = self.getref(key)
        if ref:
            ref.value = value
        else:
            assert False

    def setone(self, key, value):
        self.refs[key] = Ref(value)
        return self
