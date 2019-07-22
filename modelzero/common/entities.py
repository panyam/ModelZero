
from modelzero.core.entities import *

class BaseEntity(Entity):
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now_add=True)
