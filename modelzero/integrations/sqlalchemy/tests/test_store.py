
from datetime import datetime
import pytest
from ipdb import set_trace
from sqlalchemy import create_engine, String, DateTime, Boolean, Integer
from sqlalchemy_utils import database_exists, create_database, drop_database

from modelzero.core.records import Field
from modelzero.core.types import MZTypes
from modelzero.common.entities import BaseEntity
from modelzero.integrations.sqlalchemy import store

@pytest.fixture
def dbengine():
    # TODO - read arguments to see db name, type etc
    engine = create_engine(f"sqlite:///./test.db")
    if not database_exists(engine.url):
        create_database(engine.url)
    yield engine
    drop_database(engine.url)

class SimpleRecord(BaseEntity):
    name = Field(MZTypes.String)
    age = Field(MZTypes.Int)
    smart = Field(MZTypes.Bool)

def test_get_table(mocker, dbengine):
    sql_store = store.SQLStore(dbengine)
    table = sql_store.get_table(SimpleRecord)
    satable = table.sa_table
    assert len(satable.c) == 7
    for fname, field in SimpleRecord.__record_metadata__.items():
        col = getattr(satable.c, fname)
        assert col.name == fname
        assert col.nullable == field.optional
    assert isinstance(satable.c.__key__.type, String)
    assert isinstance(satable.c.created_at.type, DateTime)
    assert isinstance(satable.c.updated_at.type, DateTime)
    assert isinstance(satable.c.is_active.type, Boolean)
    assert isinstance(satable.c.name.type, String)
    assert isinstance(satable.c.age.type, Integer)
    assert isinstance(satable.c.smart.type, Boolean)

def test_put_table(mocker, dbengine):
    sql_store = store.SQLStore(dbengine)
    table = sql_store.get_table(SimpleRecord)
    satable = table.sa_table
    entity = SimpleRecord(is_active = True, created_at = datetime.utcnow(), updated_at = datetime.utcnow(), __key__ = "123",
            name = "Hello", age = 1000, smart = True)
    entity = table.put(entity)
