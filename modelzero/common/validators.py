
from ipdb import set_trace
from modelzero.core import errors
from modelzero.core.engine import MethodValidator

class IgnoreFields(MethodValidator):
    def __init__(self, *key_paths):
        self.key_paths = key_paths

    def __call__(self, input, *args, **kwargs):
        for keypath in self.key_paths:
            parts = keypath.split(".")
            curr = input
            parent = None
            for part in parts:
                if not curr: break
                parent = curr
                curr = parent.get(part, None)
            if parent and part in parent:
                # then remove it
                del parent[part]
        return input

class EnsureMissing(MethodValidator):
    def __init__(self, *key_paths):
        self.key_paths = key_paths

    def __call__(self, input, *args, **kwargs):
        for keypath in self.key_paths:
            parts = keypath.split(".")
            curr = input
            parent = None
            for part in parts:
                if not curr: break
                parent = curr
                curr = parent.get(part, None)
            if parent and part in parent:
                raise errors.ValidationError("keypath ({}) is supposed to be missing but found".format(keypath), keypath)
        return input

def ensure_missing(input, key_paths):
    for keypath in key_paths:
        parts = keypath.split(".")
        curr = input
        parent = None
        for part in parts:
            if not curr: break
            parent = curr
            curr = parent.get(part, None)
        if parent and part in parent:
            raise errors.ValidationError("keypath ({}) is supposed to be missing but found".format(keypath), keypath)
    return input
