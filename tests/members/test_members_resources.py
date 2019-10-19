
from .. import utils

import modelzero
from modelzero.members import resources

"""
def test_member_get(mocker):
    world = utils.create_test_world()
    ns, resclasses = resources.create_namespace(world)
    Member = resclasses["Member"]
    mocker.patch.object(world.Members, "get")
    res = utils.mockResource(Member, world)
    res.get("id1")

    world.Members.get.assert_called_once_with("id1", res._request_member)

def test_member_delete(mocker):
    world = utils.create_test_world()
    ns, resclasses = resources.create_namespace(world)
    Member = resclasses["Member"]
    mocker.patch.object(world.Members, "delete")

    res = utils.mockResource(Member, world)
    res.delete("id1")

    world.Members.delete.assert_called_once_with("id1", res._request_member)

def test_member_put(mocker):
    world = utils.create_test_world()
    ns, resclasses = resources.create_namespace(world)
    Member = resclasses["Member"]
    mocker.patch.object(world.Members, "update")

    res = utils.mockResource(Member, world)
    res.put("id1")

    world.Members.update.assert_called_once_with("id1", res._params, res._request_member)

"""
