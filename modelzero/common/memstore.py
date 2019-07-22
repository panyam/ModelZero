from ipdb import set_trace
from . import errors
from typing import TypeVar, Generic, List, Type
from .store import *
from .entities import Key

T = TypeVar("T")

class MemStore(DataStore):
    def __init__(self):
        self._tables = {}

    def get_table(self, entity_class: Type[T]) -> Table[T]:
        if entity_class not in self._tables:
            self._tables[entity_class] = MemTable(entity_class)
        return self._tables[entity_class]

class MemTable(Table[T]):
    """ A table is the logical storage provider for entities (eg as rows) and is 
    responsible for ensuring loading an persistance of Entities.
    """
    def __init__(self, entity_class : Type[T] = T):
        self._entity_class = entity_class
        self._entries = {}

    # GET methods
    def get_by_key(self, key : Key, nothrow = True) -> T:
        if type(key) is not Key:
            key = self._entity_class.Key(key)
        if key not in self._entries:
            if nothrow:
                return None
            else:
                raise errors.NotFound("Object not found for Key: " + str(key))
        return self._entries[key]

    # Update methods
    def put(self, entity : T, validate = True) -> T:
        """ Updates this entity by first validating it and then persisting it. """
        if not entity.getkey():
            # Create one - this means our entity needs auto generated keys
            import time
            now = int(time.time() * 1000)
            entity.setkey(now)
        if validate:
            entity.validate()
        self._entries[entity.getkey()] = entity
        return entity

    # Delete methods
    def delete_by_key(self, key : Key):
        """ Delete an entry given its Key. """
        if type(key) is not Key:
            key = self._entity_class.Key(key)
        if key in self._entries:
            del self._entries[key]

    def fetch(self, query : Query[T]) -> List[T]:
        """ Queries the table for entries that match a certain conditions and then sorting (if required) and returns results in a particular window. """
        results = self._entries.values()
        results = self._apply_filters(results, query.filters)
        results = self._apply_field_ordering(results, query.field_ordering)
        return [r.copy() for r in results[query.offset:query.limit]]

    def _apply_field_ordering(self, results, orderings):
        def sortfunc(a, b):
            for field,asc in orderings:
                valA = getattr(a, field)
                valB = getattr(b, field)
                cmpres = cmp(valA, valB)
                if cmpres != 0:
                    if asc:
                        return cmpres
                    else:
                        return -cmpres
            return 0
        import functools
        results.sort(key = functools.cmp_to_key(sortfunc))
        return results

    def _apply_filters(self, results, filters):
        def row_filter(result):
            for f in filters:
                # each filter is a clause
                assert f.fieldname in self._entity_class.__model_fields__, "Clause refers to field (%s) not in entity class (%s)" % (f.fieldname, self._entity_class)

                set_trace()
                value = getattr(result, f.fieldname)
            return True
        return list(filter(row_filter, results))
