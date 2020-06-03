
import logging
from ipdb import set_trace
from typing import TypeVar, Generic, List, Type
from taggedunion import CaseMatcher, case
from modelzero.core import errors, types
from modelzero.core.store import DataStore
from modelzero.core.store import Table as MZTable, Clause, Query
from modelzero.core.entities import Key, KEY_FIELD

from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Float, Binary, MetaData, Table, ForeignKeyConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

log = logging.getLogger(__name__)

T = TypeVar("T")

class SQLStore(DataStore):
    def __init__(self, dbengine):
        self.dbengine = dbengine
        self.metadata = MetaData(self.dbengine)
        self._tables = {}
        from sqlalchemy.orm import sessionmaker
        self.session = sessionmaker(bind = dbengine)

    def get_table(self, entity_class: Type[T]) -> MZTable[T]:
        if entity_class not in self._tables:
            self._tables[entity_class] = SQLTable(self, entity_class)
        return self._tables[entity_class]

class ColumnInfo(object):
    def __init__(self, name, sa_column, index, end_index = -1, parent_column = None):
        self.name = name
        self.parent_column = None
        self.sa_column = sa_column
        self.index = index
        self.end_index = end_index if end_index >= 0 else index

class Flattener(object):
    """ Currently a way to flatten schemas is to simply recursively visit all
    entries in a type and manually write a column store.  This means we would
    need to have custom serializer and deserializer methods.  Instead
    if we can represent the SQL target as a "type" then this transformation
    is very similar to how Queries can transform one type to another.  Another 
    problem with manually flattening is the parent is responsible for child types
    and will end up duplicating it.  eg 

    if two different entity types contain say a Member record, then the parent
    entity will have to flatten/unflatten this each time instead of one 
    flat/unflattener responsible for doing this regardless of the context 
    it is in.

    The way we would use this is:

    table = get_table(entity_class)
    table._sql_transformer = would be an instance of this
    table.ensure() - will make sure DB is created with all needed columns
    table._sa_columns would have *all* the columns which are obtained by
    getting the columns of all flatteners it contains
    table.put(entity), will just go through all flatteners (managing offsets) 
    to create a flatenned set
    table.get() will convert a result set by unflattening it to nested records

    Here we are decoupling offset management from flat/unflat
    """
    def __init__(self, sql_store, column_list, entity_type):
        self.entity_type = entity_type

    @property
    def num_columns(self):
        """ Returns how many columns are required to representt this type. """
        return 1

    def from_result_set(self, result_set, offset):
        """ Given a result set and an offset into it, extracts the entity
        of the given type and un-flattens it. """
        return None

    def to_result_set(self, offset, value):
        """ Flattens a value of our entity_type into the result set. """
        return None

class SQLTable(MZTable[T]):
    """ A SQL table over an entity. """
    def __init__(self, sql_store : SQLStore, entity_class : Type[T] = T):
        self.sql_store = sql_store
        self._entity_class = entity_class
        self._table_name = self._entity_class.__fqn__ # .replace(".", "_")
        self._all_columns = []
        self._field_path_index = {}
        self._sa_table = None
        self._sa_table_class = None
        self.create_table()

    @property
    def table_name(self):
        return self._table_name

    def create_table(self):
        """ Create the core SQL Alchemy Table object. """
        if self._sa_table is None:
            self._columns = []
            self._field_path_index = {}
            self._sa_table = Table(self._table_name, self.sql_store.metadata)
            field_path_index = self._field_path_index

            # First add the pkey fields
            if not self._entity_class.key_fields():
                colindex = len(self._columns)
                colname = KEY_FIELD
                self._field_path_index[colname] = colindex

                sa_column = Column(KEY_FIELD, String, primary_key = True)
                column = ColumnInfo(column.name, sa_column, colindex, -1, None)
                self._columns.append(column)
                self._sa_table.append_column(column)

            for fieldname,field in self._entity_class.__record_metadata__.items():
                self.field_to_column(field.logical_type, fieldname)

            # Add pkey constraint if they exist
            kfs = self._entity_class.key_fields() or []
            if len(kfs) == 1:
                column = self._columns[self._field_path_index[kfs[0]]]
                column.sa_column.primary_key = True
            elif len(kfs) > 1:
                # Add a PrimaryKeyConstraint
                self._sa_table.append_constraint(PrimaryKeyConstraint(*kfs))
        return self._sa_table

    @property
    def sa_table(self):
        self.create_table()
        # Also create it if it doesnt exist
        engine = self.sql_store.dbengine
        if not engine.dialect.has_table(engine, self.table_name):
            self.sql_store.metadata.create_all()
        return self._sa_table

    @property
    def sa_table_class(self):
        if self._sa_table_class is None:
            self._sa_table_class = type(self._entity_class.__name__, (self.sql_store.Base,), dict(__table__ = self.sa_table))
        return self._sa_table_class

    def field_to_column(self, field_type, field_name, optional = False):
        f2c = FieldToColumns(self)
        columns, children = f2c(field_type, field_name, optional or field_type.is_optional_type)

        # Register the column
        if type(columns) is not list: columns = [columns]
        for sa_column in columns:
            colindex = len(self._columns)
            colname = sa_column.name

            if column.name in self._field_path_index:
                set_trace()
                raise Exception(f"Column with name '{column.name}' already exists")

                sa_column = Column(KEY_FIELD, String, primary_key = True)
                column = ColumnInfo(column.name, sa_column, colindex, -1, None)
                self._columns.append(column)
                self._sa_table.append_column(column)


            self._field_path_index[column.name] = colindex
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
        set_trace()
        for k,v in entity.items():
            setattr(out, k, v)
        # set the key
        key = self._entity_class.Key(entity.key.id_or_name)
        out.setkey(key)
        return out

    def entity_to_table_fields(self, parent, fieldname, key_fields, entity_fields, prefix = ""):
        fullpath = fieldname if not prefix else (prefix + "_" + fieldname)
        value = parent.__field_values__[fieldname]
        valuetype = parent.__record_metadata__[fieldname].logical_type
        if valuetype.is_record_type:
            entity_fields[fullpath] = value is not None
            if value:
                # need to recurse
                for field,fvalue in value.__field_values__.items():
                    self.entity_to_table_fields(value, field, key_fields, entity_fields, fullpath)
        elif valuetype.is_union_type:
            set_trace()
            entity_fields[fullpath] = value is not None
        else:
            # leaf/native values
            entity_fields[fullpath] = parent.__field_values__[fieldname]

    def toDatastore(self, entity : T):
        key_fields = {}
        entity_fields = {}

        if not self._entity_class.key_fields():
            if entity.getkey():
                # Create one - this means our entity needs auto generated keys
                key_fields[KEY_FIELD] = entity.getkey().value
            else:
                set_trace()
        for field,value in entity.__field_values__.items():
            self.entity_to_table_fields(entity, field, key_fields, entity_fields)
        return key_fields, entity_fields

    # GET methods
    def get_by_key(self, key : Key, nothrow = True) -> T:
        from sqlalchemy import select, and_, or_, not_, asc, desc, all_
        stmt = select([self.sa_table])
        if type(key) is not Key:
            key = self._entity_class.Key(key)
        key_fields = self._entity_class.key_fields()
        if not key_fields:
            stmt = stmt.where(getattr(self.sa_table.c, KEY_FIELD) == key.value)
        else:
            for i,kf in enumerate(key_fields):
                stmt = stmt.where(getattr(self.sa_table.c, kf) == key.parts[i])

        results = self.sql_store.dbengine.execute(stmt)
        entity = list(map(self.fromDatastore, results))
        return entity

    # Update methods
    def put(self, entity : T, validate = True) -> T:
        """ Updates this entity by first validating it and then persisting it. """
        if validate:
            entity.validate()
        from sqlalchemy import insert
        table = self.sa_table
        cols = table.c
        stmt = table.insert()
        key_fields, entity_fields = self.toDatastore(entity)
        all_fields = dict(entity_fields, **key_fields)
        stmt = stmt.values(**all_fields)
        result = self.sql_store.dbengine.execute(stmt)
        return entity

    # Delete methods
    def delete_by_key(self, key : Key):
        if type(key) is not Key:
            key = self._entity_class.Key(key)
        """ Delete an entry given its Key. """
        dskey = self.dsclient.key(self._entity_class.__fqn__, key.value)
        self.dsclient.delete(dskey)

    OPS = {
            Clause.OP_EQ: lambda f,v: f == v,
        Clause.OP_NE: lambda f,v: f != v,
        Clause.OP_LT: lambda f,v: f < v,
        Clause.OP_LE: lambda f,v: f <= v,
        Clause.OP_GT: lambda f,v: f > v,
        Clause.OP_GE: lambda f,v: f >= v,
        Clause.OP_IN: lambda f,v: f in v,
    }

    def fetch(self, query : Query[T]) -> List[T]:
        """ Queries the table for entries that match a certain conditions and then sorting (if required) and returns results in a particular window. """
        from sqlalchemy import select, and_, or_, not_, asc, desc, all_
        table = self.sa_table
        cols = table.c
        stmt = select([table])
        efields = self._entity_class.__record_metadata__
        if query.filters:
            # assert f.fieldname in efields, "Clause refers to field (%s) not in entity class (%s)" % (f.fieldname, self._entity_class)
            and_args = [OPS[f.operator](getattr(cols, f.fieldname), f.value) for f in query.filters]
            stmt = stmt.where(and_(*and_args))
        if query.field_ordering:
            order_args = [(asc if is_asc else desc)(getattr(cols, field))  for field,is_asc in query.field_ordering]
            stmt = stmt.order_by(*order_args)
        if query.limit: stmt = stmt.limit(query.limit)
        if query.offset: stmt = stmt.offset(query.offset)
        results = self.sql_store.dbengine.execute(stmt)
        entities = list(map(self.fromDatastore, results))
        return entities

class FieldToColumns(CaseMatcher):
    __caseon__ = types.Type
    def __init__(self, sql_table):
        self.sql_table = sql_table
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
            if typearg.is_type_ref:
                typearg = typearg.target
            record_class = typearg.record_class
            # The target record could have a default pkey, custom pkey or even a composite pkey!
            source_fields = []
            target_fields = []
            if not record_class.key_fields():
                # default pkey
                source_fields = [ field_name ]
                target_fields = [f"{record_class.__fqn__}.__key__"]
                # Ensure table exists
                target_table = self.sql_table.sql_store.get_table(record_class)
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
