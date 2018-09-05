
import pytest
import os
import tempfile

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


@pytest.mark.usefixtures("build_project")
@pytest.mark.usefixtures("task_maya_animate_S01")
def test_get_timeline_data():
    data = reveries.utils.get_timeline_data()
    assert data == (101, 200, 1, 30)


@pytest.mark.usefixtures("build_project")
@pytest.mark.usefixtures("task_maya_animate_S01")
def test_compose_timeline_data():
    data = reveries.utils.compose_timeline_data()
    assert data == (100, 201, 30)


@pytest.mark.usefixtures("build_project")
@pytest.mark.usefixtures("task_maya_animate_S01")
def test_get_resolution_data():
    data = reveries.utils.get_resolution_data()
    assert data == (1920, 1080)
