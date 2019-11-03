
from modelzero.members import engine as membersengine
from modelzero.auth import engine as authengine
from modelzero.utils import resolve_fqn
import os

class World(object):
    """ All things in modelzero require a world to operate on.  The world provides the context for dependancies. """
    @classmethod
    def get(cls):
        if not hasattr(cls, "the_world"):
            setattr(cls, "the_world", cls.create())
        return cls.the_world

    @classmethod
    def create(cls):
        # this needs to be set at startup
        configs = cls.__world_config__
        datastore = cls.create_datastore(configs)
        print(f"Creating World, Configs: {configs}")
        return World(datastore)

    @classmethod
    def create_datastore(cls, configs):
        dsconfig = configs["datastore"]
        resolved, dsclass = resolve_fqn(dsconfig["class"])
        dsargs = dsconfig.get("args", []) or []
        dskwargs = dsconfig.get("kwargs", {}) or {}
        return dsclass(*dsargs, **dskwargs)

    def __init__(self, datastore = None):
        self.datastore = datastore
        self.Members = membersengine.Engine(datastore)
        self.AuthEngine = authengine.AuthEngine(datastore, self.Members)
        self.EmailAuth = authengine.EmailAuthenticator(self.AuthEngine)
        self.PhoneAuth = authengine.PhoneAuthenticator(self.AuthEngine)
        self.AuthEngine.add_authenticator("email", self.EmailAuth)
        self.AuthEngine.add_authenticator("phone", self.PhoneAuth)

