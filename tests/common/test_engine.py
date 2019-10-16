
from ipdb import set_trace
import random, datetime
import binascii, hashlib, os

import modelzero
from modelzero.core import errors
from modelzero.core.store import Query
from modelzero.common.engine import *
from modelzero.common.entities import *

def create_test_engine():
    from modelzero.common import memstore
    datastore = memstore.MemStore()
    return Engine(datastore)

def test_engine_get(mocker):
    engine = create_test_engine()
    entity_id, entity, viewer, access_type = 42, object(), object(), "view"
    mocker.patch.object(engine.table, "get_by_key", return_value = entity)
    mocker.patch.object(engine, "ensure_access")
    engine.get(entity_id, viewer, access_type)
    engine.table.get_by_key.assert_called_once_with(entity_id, nothrow = False)
    engine.ensure_access.assert_called_once_with(entity, viewer, access_type)

def test_engine_fetch(mocker):
    engine = create_test_engine()
    count,offset,viewer = 100, 10, None
    mocker.patch.object(engine.table, "fetch")
    engine.fetch(count, offset, viewer)
    engine.table.fetch.assert_called_once_with(Query(engine.entity_class).set_limit(count).set_offset(offset))

def test_soft_delete(mocker):
    engine = create_test_engine()
    entity_or_id, viewer, soft_delete = 42, BaseEntity(), True
    entity = viewer
    mocker.patch.object(engine, "get", return_value = entity)
    mocker.patch.object(engine, "ensure_access")
    mocker.patch.object(engine.table, "put")

    engine.delete(entity_or_id, viewer, soft_delete)
    engine.get.assert_called_once_with(entity_or_id)
    engine.ensure_access.assert_called_once_with(entity, viewer, "delete")
    assert entity.is_active == False
    engine.table.put.assert_called_once_with(entity)

def test_hard_delete(mocker):
    engine = create_test_engine()
    entity_or_id, viewer, soft_delete = 42, BaseEntity(), False
    entity = viewer
    mocker.patch.object(engine, "get", return_value = entity)
    mocker.patch.object(engine, "ensure_access")
    mocker.patch.object(engine.table, "delete")

    engine.delete(entity_or_id, viewer, soft_delete)
    engine.get.assert_called_once_with(entity_or_id)
    engine.ensure_access.assert_called_once_with(entity, viewer, "delete")
    engine.table.delete.assert_called_once_with(entity)

