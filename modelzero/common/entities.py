
from modelzero.core import types
from modelzero.core.entities import *
from modelzero.core.types import *
from modelzero.core.custom_fields import *
from datetime import datetime

class BaseEntity(Entity):
    is_active = Field(MZTypes.Bool, default=True, optional = True)
    created_at = DateTimeField()
    updated_at = DateTimeField(default = datetime.utcnow)
