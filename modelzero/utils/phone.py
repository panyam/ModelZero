
from modelzero.core import errors
from modelzero.utils import getLogger

import hashlib, binascii, random, datetime, os
import json, phonenumbers
log = getLogger(__name__)

def validate_phone_number(number):
    try:
        x = phonenumbers.parse(number)
        if not (phonenumbers.is_possible_number(x) and phonenumbers.is_valid_number(x)):
            raise errors.ValidationError("Not a valid phone number")
    except phonenumbers.NumberParseException as npe:
        raise errors.ValidationError(npe.message)
    number = phonenumbers.format_number(x, phonenumbers.PhoneNumberFormat.E164)
    return number

def send_sms(number, body, force_in_dev = False):
    # if is_dev_mode() and not force_in_dev:
    if not force_in_dev:
        # Dont send sms in dev unless explicitly asked to do so
        log.info("SMS To %s, Body: %s" % (number, body))
        return

    import urllib, urllib2, base64
    from modelzero import configs
    use_twilio = True
    if use_twilio:
        url = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % configs.Twilio["ACCOUNT_SID"]
        base64string = base64.b64encode('%s:%s' % (configs.Twilio["ACCOUNT_SID"], configs.Twilio["AUTH_TOKEN"]))
        req = urllib2.Request(url,
                              headers = {
                                "Authorization": "Basic %s" % base64string
                              },
                              data = urllib.urlencode({
                                'To': number,
                                'From': configs.Twilio["FROM_NUMBER"],
                                'Body': body
                              }))
    else:
        url = "https://api.plivo.com/v1/Account/%s/Message/" % configs.Plivo['AUTH_ID']
        base64string = base64.b64encode('%s:%s' % (configs.Plivo["AUTH_ID"], configs.Plivo["AUTH_TOKEN"]))
        req = urllib2.Request(url,
                              headers = {
                                "Authorization": "Basic %s" % base64string,
                                "Content-Type": "application/json"
                              },
                              data = json.dumps({
                                'src': configs.Plivo['FROM_NUMBER'],
                                'dst': number,
                                'text': body
                              }))
    try:
        resp = urllib2.urlopen(req).read()
    except urllib2.HTTPError as exc:
        log.error(exc.read())
