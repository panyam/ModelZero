
from typing import TypeVar, Generic, List, Union, Type
from modelzero.core.engine import EngineMethod
from modelzero.core.engine import Engine as CoreEngine
from modelzero.core.entities import Key, Entity
from modelzero.core.store import Query
from .validators import ensure_missing

T = TypeVar("T", bound = Entity)
M = TypeVar("M")

class Engine(Generic[T, M], CoreEngine):
    @EngineMethod
    def get(self, obj_or_id : Union[T, Key], viewer : M = None, access_type : str = "view", nothrow = False):
        entity = obj_or_id
        if type(obj_or_id) is not self.model_class:
            entity = self.table.get_by_key(obj_or_id, nothrow = nothrow)
        if viewer:
            self.ensure_access(entity, viewer, access_type)
        return entity

    @EngineMethod
    def fetch(self, count : int = 1000, offset : int = 0, viewer : M = None):
        """ Get all the members."""
        query = Query(self.model_class).set_limit(count).set_offset(offset)
        return self.table.fetch(query)

    @EngineMethod
    def delete(self, entity_or_id : Union[T, Key], viewer : M, soft_delete : bool = False):
        entity = self.get(entity_or_id)
        self.ensure_access(entity, viewer, "delete")
        if soft_delete:
            from datetime import datetime
            entity.is_active = False
            entity.updated_at = datetime.now()
            self.table.put(entity)
        else:
            # TODO: Delete *everything* else about this entity
            self.table.delete(entity)

    @EngineMethod
    @EngineMethod.ValidateParam("patch", ensure_missing, ["__key__", "created_at"])
    def update(self, entity : T, patch : dict):
        entity.apply_patch(patch)
        self.table.put(entity)
        return entity 

    @EngineMethod.ValidateParam("entity", ensure_missing, ["__key__"])
    def create(self, entity : T, viewer = None):
        return self.table.put(entity)

    def ensure_access(self, target_member : M, accessor : M, permission : str):
        """
        Return true if *accessor* can access the target_member for a particular permission.
        If not a NotAllowed exception is raised.
        """
        if not permission: 
            return True
        if accessor is None:
            raise errors.NotAllowed("Accessor not found")
        if target_member != accessor:
            raise errors.NotAllowed("Access not allowed for permission '%s'" % permission)
        return True
