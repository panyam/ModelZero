
import datetime
from modelzero.core.types import MZTypes
from modelzero.common.entities import BaseEntity
from modelzero.common.fields import Field, DateTimeField

class Member(BaseEntity):
    fullname = Field(MZTypes.String, required = True)
    date_of_birth = DateTimeField(required = True)
    phone = Field(MZTypes.String, default="", indexed = True)
    email = Field(MZTypes.String, default="", indexed = True)

    @property
    def age(self):
        """ Returns a user's age in days. """
        return (datetime.datetime.utcnow() - self.date_of_birth).days

    def time_till_age(self, targetage):
        """ Returns the number of days remaining till a given age. """
        days_remaining = (targetage * 365) - self.age
        return days_remaining

