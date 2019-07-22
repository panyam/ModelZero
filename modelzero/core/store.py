
from . import errors
from typing import TypeVar, Generic, List, Mapping, Type, Any
from .entities import Key

T = TypeVar("T")

class Clause(object):
    OP_EQ = 0
    OP_NE = 1
    OP_LT = 2
    OP_LE = 3
    OP_GT = 4
    OP_GE = 5
    OP_IN = 6
    operators = {
        'eq': OP_EQ,
        'ne': OP_IN,
        'lt': OP_LT,
        'le': OP_LE,
        'gt': OP_GT,
        'ge': OP_GE,
        'in': OP_IN,
    }

    def __init__(self, param, value):
        self.fieldname = param
        self.operator = "eq"
        self.value = value
        for op,opval in Clause.operators.items():
            if param.endswith("__" + op):
                self.fieldname = self.fieldname[:-(2 + len(op))]
                self.operator = opval
                break

    def __eq__(self, another):
        if type(another) != Clause: return False
        if self.fieldname != another.fieldname: return False
        if self.operator != another.operator: return False
        if self.value != another.value: return False
        return True

class Query(Generic[T]):
    """ Generic Query interface that our tables can execute. """
    def __init__(self, entity_class : Type[T]):
        self.entity_class = entity_class
        self._offset = 0
        self._limit = 100
        self._field_ordering = []
        self._filter_clauses = []
        self._projection = []

    def __eq__(self, another):
        if type(another) != Query: return False
        if self._offset != another._offset: return False
        if self._limit != another._limit: return False
        if self._field_ordering != another._field_ordering: return False
        if self._projection != another._projection: return False
        if self._filter_clauses != another._filter_clauses: return False
        return True

    @property
    def offset(self):
        return self._offset

    def set_offset(self, pos = 0) -> "Query":
        return self

    @property
    def limit(self):
        return self._limit

    def set_limit(self, count = 100) -> "Query":
        self._limit = count
        return self

    @property
    def has_ordering(self):
        return len(self._field_ordering) > 0

    @property
    def field_ordering(self):
        return self._field_ordering

    def order_by(self, fieldname, ascending = True) -> "Query":
        self._field_ordering.append((fieldname, ascending))
        return self

    @property
    def has_filters(self):
        return len(self._filter_clauses) > 0

    @property
    def filters(self):
        return self._filter_clauses

    def add_filter(self, *clauses : List[Clause], **kwargs : Mapping[str, Any]) -> "Query":
        for clause in clauses:
            self._add_clause(clause)
        for arg,value in kwargs.items():
            self._add_clause(Clause(arg, value))
        return self

    def _add_clause(self, clause : Clause) -> "Query":
        # validate clase
        assert clause.fieldname in self.entity_class.__model_fields__, "%s does not contain field %s" % (str(self.entity_class), clause.fieldname)
        self._filter_clauses.append(clause)
        return self

    @property
    def projection(self):
        return self._projection

    def set_projection(self, field_names : List[str] = None) -> "Query":
        self._projection = field_names
        return self

class Table(Generic[T]):
    """ A table is the logical storage provider for entities (eg as rows) and is 
    responsible for ensuring loading an persistance of Entities.
    """
    # GET methods
    def batch_get(self, keys : List[Key]) -> Mapping[Key, T]:
        """ Batch fetch a set of entities given their Keys. """
        return [self.get_by_key(key) for key in keys]

    def get_by_key(self, key : Key, nothrow = False) -> T:
        assert False, "Not implemented"

    # Update methods
    def batch_put(self, entities : List[T]):
        """ Batch put a set of entities. """
        # TODO - return futures
        return [self.put(entity) for entity in entities]

    def put(self, entity : T, validate = True):
        """ Updates this entity by first validating it and then persisting it. """
        if validate:
            entity.validate_fields()
            entity.validate()
        return False

    # Delete methods
    def batch_delete(self, keys : List[Key]):
        """ Batch delete a set of entities given their Keys. """
        for key in keys: self.delete_by_key(key)

    def delete(self, entity : T):
        """ Delete an entity. """
        return self.delete_by_key(entity.getkey())

    def delete_by_key(self, key : Key):
        """ Delete an entry given its Key. """
        assert False, "Not implemented"

    def fetch(self, query : Query[T]) -> List[T]:
        """ Queries the table for entries that match a certain conditions and then sorting (if required) and returns results in a particular window. """
        return []

class DataStore(object):
    """ A DataStore is a collection of tables for storing entities of different types. """
    def get_table(self, entity_class: Type[T]) -> Table[T]:
        pass

