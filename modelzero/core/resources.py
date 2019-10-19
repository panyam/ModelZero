
from __future__ import unicode_literals, absolute_import
from ipdb import set_trace
import json
from functools import wraps
from flask import request
from flask_restplus import Resource, fields
from modelzero import utils as neutils
from . import errors

def create_login_url(redirto):
    base_url = "http://localhost:8080/"
    return base_url + "/auth/login/?to=" + base_url + redirto

def handle_api_errors(handler):
    @wraps(handler)
    def decorated_handler(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except errors.NotFound as error:
            return neutils.error_json(error.message), 404
        except errors.NotAllowed as error:
            return neutils.error_json(error.message), 403
        except errors.NotAllowed as error:
            return neutils.error_json(error.message), 403
        except errors.Unauthorized as error:
            return neutils.error_json(error.message), 401, {'Location': create_login_url('/mysession/')}
        except errors.ValidationError as error:
            return neutils.error_json(error.message), 400
    return decorated_handler

class BaseResource(Resource):
    method_decorators = [ handle_api_errors ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "world" not in kwargs: set_trace()
        self.world = kwargs.pop("world")
        self._request_member = None
        self._request_channel = None
        self._params = kwargs.get("params", None)

    @property
    def params(self):
        if self._params is None:
            self._params = RequestParamSource(request)
        return self._params

    @property
    def request_channel(self):
        # Looks like a circular dependancy?
        # TODO: AuthEngine should not know about "request" objects 
        if self._request_channel is None:
            self._request_channel = self.world.Auth.get_channel_from_request(request)
        return self._request_channel

    @property
    def request_member(self):
        if self._request_member is None and self.request_channel.memberkey:
            self._request_member = self.world.Members.table.get_by_key(self.request_channel.memberkey)
        return self._request_member

class RequestParamSource(object):
    def __init__(self, request):
        self.request = request
        self.request_json = self.request.get_json()

    def __contains__(self, key):
        if self.request.values and key in self.request.values:
            return True

        if self.request_json and key in self.request_json:
            return True

        if self.request.args and key in self.request.args:
            return True

        return False

    def get(self, param_name, on_missing = None):
        if param_name in self.request.values:
            param_value = self.request.values.get(param_name)
        else:
            rj = self.request_json
            if rj and param_name in rj:
                param_value = rj.get(param_name)
            else:
                # Try query params
                param_value = self.request.args.get(param_name, on_missing)
        return param_value

    def items(self):
        return self.request.values.items()

