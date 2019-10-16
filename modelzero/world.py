
from modelzero.members import engine as membersengine
from modelzero.auth import engine as authengine

class World(object):
    """ All things in modelzero require a world to operate on.  The world provides the context for dependancies. """
    def __init__(self, datastore):
        self.datastore = datastore
        self.Members = membersengine.Engine(datastore)
        self.Auth = authengine.AuthEngine(datastore, self.Members)
        self.Auth.add_authenticator("email", authengine.EmailAuthenticator(self.Auth))
        self.Auth.add_authenticator("phone", authengine.PhoneAuthenticator(self.Auth))
