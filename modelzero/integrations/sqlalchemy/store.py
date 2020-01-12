
import logging
from ipdb import set_trace
from typing import TypeVar, Generic, List, Type
from taggedunion import CaseMatcher, case
from modelzero.core import errors, types
from modelzero.core.store import DataStore
from modelzero.core.store import Table as MZTable, Clause, Query
from modelzero.core.entities import Key

from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Float, Binary, MetaData, Table, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

log = logging.getLogger(__name__)

T = TypeVar("T")

class SQLStore(DataStore):
    def __init__(self, dbengine):
        self.dbengine = dbengine
        self.Base = declarative_base()
        self.metadata = MetaData()
        self._tables = {}
        from sqlalchemy.orm import sessionmaker
        self.session = sessionmaker(bind = dbengine)

    def get_table(self, entity_class: Type[T]) -> MZTable[T]:
        if entity_class not in self._tables:
            self._tables[entity_class] = SQLTable(self, entity_class)
        return self._tables[entity_class]

class SQLTable(MZTable[T]):
    """ A SQL table over an entity. """
    def __init__(self, sql_store : SQLStore, entity_class : Type[T] = T):
        self.sql_store = sql_store
        self._entity_class = entity_class
        self._columns = []
        self._field_path_index = {}
        self._sa_table = None
        self._sa_table_class = None

    @property
    def table_class(self):
        if self._sa_table_class is None:
            self._columns = []
            self._field_path_index = {}
            self._sa_table = Table(self._entity_class.__fqn__, self.sql_store.metadata)
            field_path_index = self._field_path_index

            # First add the pkey fields
            if not self._entity_class.key_fields():
                column = Column(KEY_FIELD, String, primary_key = True)
                self._field_path_index[column.name] = len(self._columns)
                self._columns.append(column)
                self._sa_table.append_column(column)

            for fieldname,field in self._entity_class.__record_metadata__.items():
                self.field_to_column(field.logical_type, fieldname)

            # Add pkey constraint if they exist
            for kf in self._entity_class.key_fields() or []:
                column = self._columns[self._field_path_index[kf]]
                column.primary_key = True

            # setup the field and table level constraints
            self._sa_table_class = type(self._entity_class.__name__, (self.sql_store.Base,), dict(__table__ = self._sa_table))
            set_trace()
        return self._sa_table_class

    def field_to_column(self, field_type, field_name, optional = False):
        f2c = FieldToColumns()
        columns, children = f2c(field_type, field_name, optional or field_type.is_optional_type)

        # Register the column
        if type(columns) is not list: columns = [columns]
        for column in columns:
            if column.name in self._field_path_index:
                set_trace()
                raise Exception(f"Column with name '{column.name}' already exists")
            self._field_path_index[column.name] = len(self._columns)
            self._columns.append(column)
            self._sa_table.append_column(column)

        # Add any constraints
        for fkc in f2c.fkey_constraints:
            self._sa_table.append_constraint(fkc)

        # Proceed to the children
        child_optional = optional or field_type.is_optional_type or field_type.is_sum_type or field_type.is_union_type
        for childname,childtype in children:
            ourname = field_name + "_" + childname
            self.field_to_column(childtype, ourname, child_optional)

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
        self.table_class
        dsquery = self.dsclient.query(kind = self._entity_class.__fqn__)
        efields = self._entity_class.__record_metadata__
        for f in query.filters:
            assert f.fieldname in efields, "Clause refers to field (%s) not in entity class (%s)" % (f.fieldname, self._entity_class)
            dsquery.add_filter(f.fieldname,
                               SQLTable.OPS[f.operator],
                               f.value)
        if query.field_ordering:
            dsquery.order = [field if asc else "-"+ field for field,asc in query.field_ordering]
        results = dsquery.fetch(limit = query.limit, offset = query.offset)
        entities = list(map(self.fromDatastore, results))
        return entities

class FieldToColumns(CaseMatcher):
    __caseon__ = types.Type
    def __init__(self):
        self.fkey_constraints = []

    @case("record_type")
    def for_record_type(self, type_data : types.RecordType, field_name : str, optional : bool = False):
        # Just holds if the value is null or not
        column = Column(field_name, Boolean, nullable = optional)
        return None, type_data.record_class.__record_metadata__.items()

    @case("product_type")
    def for_product_type(self, type_data : types.ProductType, field_name : str, optional : bool = False):
        # Just holds if the value is null or not
        column = Column(field_name, Boolean, nullable = optional)
        return column, ftype.children

    @case("union_type")
    def for_union_type(self, type_data : types.UnionType, field_name : str, optional : bool = False):
        column = Column(field_name, TINYINT, nullable = optional)
        return column, ftype.union_class.__variants__

    @case("sum_type")
    def for_sum_type(self, type_data : types.SumType, field_name : str, optional : bool = False):
        # Holds a value which tells which variant is active.
        column = Column(field_name, TINYINT, nullable = optional)
        return column, ftype.children

    @case("opaque_type")
    def for_opaque_type(self, type_data : types.OpaqueType, field_name : str, optional : bool = False):
        if type_data == types.MZTypes.Bool.opaque_type:
            return Column(field_name, Boolean, nullable = optional), []
        if type_data == types.MZTypes.Int.opaque_type:
            return Column(field_name, Integer, nullable = optional), []
        if type_data == types.MZTypes.Float.opaque_type:
            return Column(field_name, Float, nullable = optional), []
        if type_data == types.MZTypes.String.opaque_type:
            return Column(field_name, String, nullable = optional), []
        if type_data == types.MZTypes.DateTime.opaque_type:
            return Column(field_name, DateTime, nullable = optional), []
        if type_data == types.MZTypes.Bytes.opaque_type:
            return Column(field_name, Binary, nullable = optional), []
        if type_data == types.MZTypes.URL.opaque_type:
            return Column(field_name, String, nullable = optional), []
        set_trace()
        pass

    @case("type_app")
    def for_type_app(self, type_app : types.TypeApp, field_name : str, optional : bool = False):
        origin_type = type_app.origin_type
        if not origin_type.is_opaque_type:
            set_trace()
            raise Exception("Arbitrary Generics not yet supported")

        opaque_type = origin_type.opaque_type
        if origin_type == types.MZTypes.List:
            return Column(field_name, Binary, nullable = optional), []
        elif origin_type == types.MZTypes.Map:
            set_trace()
            a = 2
        elif origin_type == types.MZTypes.Key:
            # Nothing to be done - should be taken care by 
            # above
            typearg = type_app.type_args[0]
            record_class = typearg.record_class
            # The target record could have a default pkey, custom pkey or even a composite pkey!
            source_fields = []
            target_fields = []
            if not record_class.key_fields():
                # default pkey
                source_fields = [ field_name ]
                target_fields = [f"{record_class.__fqn__}.__key__"]
                columns = [Column(field_name, String, nullable = optional)]
            else:
                # possibly composite key 
                # get *all* fields from the target_fields.  A complication here is even if there is a single key field,
                # key fields are allowed to be composite objects - like 
                set_trace()
                for kf in record_class.key_fields():
                    set_trace()
                    a = 3
                columns = []
            self.fkey_constraints.append(ForeignKeyConstraint(source_fields, target_fields))
            return columns, []
        else:
            set_trace()
            raise Exception("Invalid generic container")

    @case("type_var")
    def for_type_var(self, type_var : types.TypeVar, field_name : str, optional : bool = False):
        set_trace()
        pass

    @case("type_ref")
    def for_type_ref(self, type_ref : types.TypeRef, field_name : str, optional : bool = False):
        return self(type_ref.target, field_name, optional)

    @case("func_type")
    def for_func_type(self, type_data : types.FuncType, field_name : str, optional : bool = False):
        # Nothing to be done - func types not saved in DB
        return None, []

    @case("optional_type")
    def for_optional_type(self, type_data : types.OptionalType, field_name : str, optional : bool = False):
        return self(type_data.base_type, field_name, True)
