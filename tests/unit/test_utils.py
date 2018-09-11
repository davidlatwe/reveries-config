
import pytest
import os
import tempfile

try:
    import mock
except ImportError:
    import unittest.mock as mock

import reveries
import reveries.utils


def test_temp_dir():
    prefix = "test_temp"
    dir_path = reveries.utils.temp_dir(prefix=prefix)

    # It's a dir
    assert os.path.isdir(dir_path)
    # The dir is empty
    assert len(os.listdir(dir_path)) == 0
    # The dir named with prefix
    assert os.path.basename(dir_path).startswith(prefix)

    os.rmdir(dir_path)  # clean up


def test_clear_stage():
    prefix = "test_clear"
    tmp_1 = tempfile.mkdtemp(prefix=prefix)
    tmp_2 = tempfile.mkdtemp(prefix=prefix)

    reveries.utils.clear_stage(prefix=prefix)

    # They should be all removed
    assert os.path.isdir(tmp_1) is False
    assert os.path.isdir(tmp_2) is False


@mock.patch.dict('avalon.Session', {"AVALON_ASSET": "TestShot"})
@mock.patch('avalon.io.find_one')
def test_get_timeline_data(find_one):

    def make_side_effect(project=None, asset=None):
        keys = ["edit_in", "edit_out", "handles", "fps"]
        project_data = dict(zip(keys, project)) if project else {}
        asset_data = dict(zip(keys, asset)) if asset else {}

        def side_effect(spec):
            if spec == {"type": "project"}:
                return {"data": project_data}
            if spec == {"name": "TestShot", "type": "asset"}:
                return {"data": asset_data}

        return side_effect

    # Only poject has time data
    PROJECT_DATA = (100, 999, 1, 24)
    find_one.side_effect = make_side_effect(PROJECT_DATA)
    data = reveries.utils.get_timeline_data()
    assert data == PROJECT_DATA

    # Asset has time data, should use asset data
    ASSET_DATA = (200, 400, 10, 30)
    find_one.side_effect = make_side_effect(PROJECT_DATA, ASSET_DATA)
    data = reveries.utils.get_timeline_data()
    assert data == ASSET_DATA

    # Handle is invalid
    INVALID_DATA = (100, 999, 0, 24)
    find_one.side_effect = make_side_effect(INVALID_DATA)
    with pytest.raises(ValueError):
        reveries.utils.get_timeline_data()


@mock.patch('reveries.utils.get_timeline_data')
def test_compose_timeline_data(time_data):

    time_data.return_value = (100, 200, 10, 24)

    data = reveries.utils.compose_timeline_data()
    assert data == (90, 210, 24)


@mock.patch('avalon.io.find_one')
def test_get_resolution_data(find_one):

    find_one.return_value = {
        "data": {
            "resolution_width": 960,
            "resolution_height": 540,
        }
    }
    data = reveries.utils.get_resolution_data()
    assert data == (960, 540)

    # Test default value
    find_one.return_value = {"data": {}}
    data = reveries.utils.get_resolution_data()
    assert data == (1920, 1080)


@mock.patch('pyblish_qml.ipc.formatting.format_result')
def test_publish_results_formatting(format_result):

    fake_format = (lambda res: res * 2)
    format_result.side_effect = fake_format

    results = [1, 2, 3]
    context = mock.Mock()
    context.data = {"results": results}

    formatted = reveries.utils.publish_results_formatting(context)
    assert formatted == list(map(fake_format, results))


def test_hash_file():
    prefix = "test_hash"
    wdir = tempfile.mkdtemp(prefix=prefix)
    file_path = os.path.join(wdir, "foo.bar")
    with open(file_path, "w") as foo:
        foo.write("")

    empty_file_hash_val = """c459dsjfscH38cYeXXYogktxf4Cd9ibshE3BHUo6a58hBXmRQd
ZrAkZzsWcbWtDg5oQstpDuni4Hirj75GEmTc1sFT"""

    hash_val = reveries.utils.hash_file(file_path)

    assert hash_val.startswith("c4")
    assert hash_val == empty_file_hash_val.replace("\n", "")


@mock.patch('pyblish.api.discover')
def test_plugins_by_range(discover):

    def plugin_mock(order):
        Plugin = type("Plugin", (object,), dict())
        plugin = Plugin()
        plugin.__dict__["order"] = order
        return plugin

    plugins = [plugin_mock(i) for i in (0, 0.1, 1, 1.2, 1.8, 2.2, 3, 3.1)]

    discover.return_value = plugins

    found = reveries.utils.plugins_by_range(base=2, offset=1)
    assert len(found) == 4
    assert [p.order for p in found] == [1, 1.2, 1.8, 2.2]


def test_asset_hasher():

    # Hashing non-empty file\
    #
    prefix = "test_hash"
    wdir = tempfile.mkdtemp(prefix=prefix)
    file_path = os.path.join(wdir, "foo.bar")

    # This data happens to be able to cover the if-statement inside
    # `AssetHasher.hash()`:
    # ```
    # if len(b58_hash) < (c4_id_length - 2):
    #     padding = "1" * (c4_id_length - 2 - len(b58_hash))
    # ```
    data = " " * 4096 * 10

    with open(file_path, "w") as foo:
        foo.write(data)

    hasher = reveries.utils.AssetHasher()
    hasher.add_file(file_path)

    hash_val = hasher.hash()
    assert hash_val.startswith("c4")

    hasher.clear()

    # Hashing dir
    #
    dir_path = os.path.dirname(reveries.__file__)
    hasher.add_dir(dir_path)

    hash_val = hasher.hash()
    assert hash_val.startswith("c4")

    hasher.clear()

    # Hashing dir (non-recursive)
    #
    hasher.add_dir(dir_path, recursive=False)

    hash_val = hasher.hash()
    assert hash_val.startswith("c4")

    hasher.clear()
