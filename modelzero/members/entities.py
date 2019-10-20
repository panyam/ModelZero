
import datetime
from modelzero.core.entities import Entity, StringField, BooleanField, IntegerField, DateTimeField, JsonField, RefField
from modelzero.common.entities import *

class Member(BaseEntity):
    fullname = StringField(required = True)
    date_of_birth = DateTimeField(required = True)
    phone = StringField(default="", indexed = True)
    email = StringField(default="", indexed = True)

    @property
    def age(self):
        """ Returns a user's age in days. """
        return (datetime.datetime.utcnow() - self.date_of_birth).days

    def time_till_age(self, targetage):
        """ Returns the number of days remaining till a given age. """
        days_remaining = (targetage * 365) - self.age
        return days_remaining

    def to_json(self):
        return {
            'id': self.key,
            'fullname': self.fullname,
            'email': self.email,
            'is_active': self.is_active,
            'phone': self.phone,
            'date_of_birth': self.date_of_birth,
            'updated_at': self.updated_at,
            'created_at': self.created_at
        }

