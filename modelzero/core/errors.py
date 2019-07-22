
class SLException(Exception):
    def __init__(self, msg, data = None):
        Exception.__init__(self, msg)
        self.message = msg
        self.data = data

class Unauthorized(SLException): pass
class NotFound(SLException): pass
class NotAllowed(SLException): pass
class ValidationError(SLException): pass
