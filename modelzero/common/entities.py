
from modelzero.core.entities import *
from modelzero.core.custom_fields import *

class BaseEntity(Entity):
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now_add=True)
