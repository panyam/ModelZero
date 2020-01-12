
from datetime import datetime
from modelzero.core.entities import Entity
from modelzero.core.types import MZTypes
from modelzero.common.fields import DateTimeField, Field

class BaseEntity(Entity):
    is_active = Field(MZTypes.Bool, default=True, optional = True)
    created_at = DateTimeField(default = datetime.utcnow)
    updated_at = DateTimeField(default = datetime.utcnow)
