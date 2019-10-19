
from modelzero.members import engine as membersengine
from modelzero.auth import engine as authengine

class World(object):
    """ All things in modelzero require a world to operate on.  The world provides the context for dependancies. """
    def __init__(self, datastore):
        self.datastore = datastore
        self.Members = membersengine.Engine(datastore)
        self.AuthEngine = authengine.AuthEngine(datastore, self.Members)
        self.EmailAuth = authengine.EmailAuthenticator(self.AuthEngine)
        self.PhoneAuth = authengine.PhoneAuthenticator(self.AuthEngine)
        self.AuthEngine.add_authenticator("email", self.EmailAuth)
        self.AuthEngine.add_authenticator("phone", self.PhoneAuth)
