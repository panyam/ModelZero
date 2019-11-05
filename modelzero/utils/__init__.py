
import importlib
import logging
import os, datetime
from modelzero.core import errors
from flask import json

from werkzeug.routing import BaseConverter

DEFAULT_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

def with_metaclass(meta, base=object, BaseName = "NewBase"):
    return meta(BaseName, (base,), {})

def getLogger(name, level = logging.INFO):
    log = logging.getLogger(name)
    log.setLevel(level)
    return log

def error_json(value): return {'message': value}

class NEJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime(DEFAULT_DATETIME_FORMAT)
        elif isinstance(obj, bytes):
            return obj.decode()
        # elif isinstance(obj, ndb.Key): return obj.id()
        elif hasattr(obj, "to_json"):
            return obj.to_json()
        elif isinstance(obj, bytes):
            return obj.decode()
        return super(NEJsonEncoder, self).default(obj)

def nonempty(s):
    if s is None or not s.strip():
        return None
    return s


class LongConverter(BaseConverter):
    def to_python(self, value):
        return long(value)

    def to_url(self, value):
        return str(value)

def ensure_date(date_format = DEFAULT_DATE_FORMAT):
    import datetime
    def ensurer(strinput):
        try:
            return datetime.datetime.strptime(strinput, date_format)
        except ValueError as ve:
            raise errors.ValidationError(ve.message)
    return ensurer

def datetime_from_now(delta_in_seconds):
    if type(delta_in_seconds) not in (float, long, int):
        raise errors.ValidationError("Expected long/float, found: %s" % str(type(delta_in_seconds)))

    return datetime.datetime.utcnow() + datetime.timedelta(0, delta_in_seconds)

def datetime_from_timestamp(timestamp_or_datetime):
    if type(timestamp_or_datetime) is datetime.datetime:
        return timestamp_or_datetime
    return datetime.datetime.fromtimestamp(timestamp_or_datetime)

def get_param(source, param_name, validator=None, required=True, default=None, setto = None, no_null = True):
    """
    A wrapper on a get-able source to allow validators as well.

    Parameters:
        source      -   An interface that provides a get method to obtain a value by key and a check for containment.
        param_name  -   Name of the parameter whose value is to be fetched.
        validator   -   The validator function to be applied (if one exists).
        required    -   Ensures that the value actually exists 
                        before validation is applied.
        default     -   If a value does not exist, then a default 
                        is used (before validation is applied).
        no_null     -   If True then a ValidationError is raised
                        if the validator function returns a None
                        value (even if it does not raise an exception).
    """
    provided = param_name in source
    if required and default is None and not provided:
        raise errors.ValidationError("Param '%s' required but not provided and default is None." % param_name)

    if not provided:
        value = default
    else:
        value = source.get(param_name)

    # Validate the value if it is required *or* provided
    if required or provided:
        if validator:
            if type(validator) is list:
                for v in validator:
                    value = v(value)
            else:
                value = validator(value)
        if value is None and no_null:
            raise errors.ValidationError("Parameter '%s' was found but validation return a null value." % param_name)

        if setto is not None:
            target, attr = setto
            setattr(target, attr, value)
    return value

def resolve_fqn(fqn):
    resolved = type(fqn) is not str
    result = fqn
    if not resolved:
        parts = fqn.split(".")
        first,last = parts[:-1],parts[-1]
        module = ".".join(first)
        module = importlib.import_module(module)
        result = getattr(module, last)
        resolved = True
    return resolved, result
