
from google.cloud import datastore
from ipdb import set_trace
from typing import TypeVar, Generic, List, Type
from modelzero.core import errors
from modelzero.core.store import *
from modelzero.core.entities import Key

import logging
log = logging.getLogger(__name__)

T = TypeVar("T")

class GAEStore(DataStore):
    def __init__(self, gae_app_id):
        self._dsclient = datastore.Client(gae_app_id)
        self._tables = {}

    def get_table(self, entity_class: Type[T]) -> Table[T]:
        if entity_class not in self._tables:
            self._tables[entity_class] = GAETable(self._dsclient, entity_class)
        return self._tables[entity_class]

class GAETable(Table[T]):
    """ A table is the logical storage provider for entities (eg as rows) and is 
    responsible for ensuring loading an persistance of Entities.
    """
    def __init__(self, dsclient, entity_class : Type[T] = T):
        self._dsclient = dsclient
        self._entity_class = entity_class

    @property
    def dsclient(self): return self._dsclient

    def fromDatastore(self, entity) -> T:
        if entity is None:
            return None
        builtin_list = list
        if isinstance(entity, builtin_list):
            entity = entity.pop()
        out = self._entity_class()
        for k,v in entity.items():
            setattr(out, k, v)
        # set the key
        key = self._entity_class.Key(entity.key.id_or_name)
        out.setkey(key)
        return out

    def toDatastore(self, entity : T):
        dsc = self.dsclient
        if entity.getkey():
            # Create one - this means our entity needs auto generated keys
            key = dsc.key(self._entity_class.__fqn__, entity.getkey().value)
        else:
            key = dsc.key(self._entity_class.__fqn__)
        dsentity = datastore.Entity(key=key)
        for field,value in entity.__field_values__.items():
            if type(value) is Key:
                dsentity[field] = value.value
            else:
                dsentity[field] = value
        return dsentity

    # GET methods
    def get_by_key(self, key : Key, nothrow = True) -> T:
        if type(key) is not Key:
            key = self._entity_class.Key(key)
        dskey = self.dsclient.key(self._entity_class.__fqn__, key.value)
        value = self.dsclient.get(dskey)
        if not value:
            if not nothrow:
                raise errors.NotFound("Object not found for Key: " + str(key))
            return None
        # convert it to entity
        return self.fromDatastore(value)

    # Update methods
    def put(self, entity : T, validate = True) -> T:
        """ Updates this entity by first validating it and then persisting it. """
        if validate:
            entity.validate()
        dsentity = self.toDatastore(entity)
        self.dsclient.put(dsentity)
        return self.fromDatastore(dsentity)

    # Delete methods
    def delete_by_key(self, key : Key):
        if type(key) is not Key:
            key = self._entity_class.Key(key)
        """ Delete an entry given its Key. """
        dskey = self.dsclient.key(self._entity_class.__fqn__, key.value)
        self.dsclient.delete(dskey)

    OPS = {
        Clause.OP_EQ: "=",
        Clause.OP_NE: "!=",
        Clause.OP_LT: "<",
        Clause.OP_LE: "<=",
        Clause.OP_GT: ">",
        Clause.OP_GE: ">=",
        Clause.OP_IN: "in",
    }

    def fetch(self, query : Query[T]) -> List[T]:
        """ Queries the table for entries that match a certain conditions and then sorting (if required) and returns results in a particular window. """
        dsquery = self.dsclient.query(kind = self._entity_class.__fqn__)
        efields = self._entity_class.__model_fields__
        for f in query.filters:
            assert f.fieldname in efields, "Clause refers to field (%s) not in entity class (%s)" % (f.fieldname, self._entity_class)
            dsquery.add_filter(f.fieldname, GAETable.OPS[f.operator], f.value)
        if query.field_ordering:
            dsquery.order = [field if asc else "-"+ field for field,asc in query.field_ordering]
        results = dsquery.fetch(limit = query.limit, offset = query.offset)
        entities = list(map(self.fromDatastore, results))
        return entities
