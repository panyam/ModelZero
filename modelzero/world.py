
from modelzero.members import engine as membersengine
from modelzero.auth import engine as authengine
import os

def create_default_datastore(**kwargs):
    fds = os.environ.get("FLASK_DATA_STORE", "mem")
    if fds == "mem":
        from modelzero.common import memstore
        datastore = memstore.MemStore()
    elif fds == "gae":
        from modelzero.integrations.gae import store
        datastore = store.GAEStore(gae_app_id = kwargs["gae_app_id"])
    return datastore

class World(object):
    """ All things in modelzero require a world to operate on.  The world provides the context for dependancies. """
    def __init__(self, datastore = None):
        self.datastore = datastore or create_default_datastore()
        self.Members = membersengine.Engine(datastore)
        self.AuthEngine = authengine.AuthEngine(datastore, self.Members)
        self.EmailAuth = authengine.EmailAuthenticator(self.AuthEngine)
        self.PhoneAuth = authengine.PhoneAuthenticator(self.AuthEngine)
        self.AuthEngine.add_authenticator("email", self.EmailAuth)
        self.AuthEngine.add_authenticator("phone", self.PhoneAuth)
