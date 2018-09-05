
from tempfile import mkdtemp

import pytest
import os
import shutil
import avalon
import avalon.inventory

PROJECT_ROOT = mkdtemp(prefix="cnftest") + os.environ["AVALON_PROJECTS"]
PROJECT_NAME = "AdventureTime"

os.environ["AVALON_PROJECTS"] = PROJECT_ROOT
os.environ["AVALON_PROJECT"] = PROJECT_NAME
os.environ["AVALON_CONFIG"] = "reveries"

PROJECT_PATH = os.path.join(PROJECT_ROOT, PROJECT_NAME)
CONFIG_TOML = os.path.join(PROJECT_PATH, ".config.toml")
INVENT_TOML = os.path.join(PROJECT_PATH, ".inventory.toml")


def _load_toml(fname):
    with open(fname) as f:
        data = avalon.vendor.toml.load(f)
    return data


def project_data():
    shutil.copyfile("res/.config.toml", CONFIG_TOML)
    shutil.copyfile("res/.inventory.toml", INVENT_TOML)
    config = _load_toml(CONFIG_TOML)
    inventory = _load_toml(INVENT_TOML)

    inventory["assets"] = [
        {
            "name": "Fin",
            "label": "Dummy",
            "tasks": ["lookdev", "model", "rig"]
        },
    ]

    inventory["shots"] = [
        {
            "name": "S01",
            "label": "S01",
            "tasks": ["animate", "layout"]
        },
    ]

    return config, inventory


@pytest.fixture(scope="session")
def build_project():

    # Init environment
    avalon.io.install()

    # Ensure clean database
    avalon.io.drop()

    # Write data
    os.makedirs(PROJECT_PATH)
    avalon.inventory.save(PROJECT_NAME, *project_data())

    yield
    # Teardown
    avalon.io.drop()
    shutil.rmtree(PROJECT_ROOT, ignore_errors=True)


@pytest.fixture
def task_maya_model_Fin():
    avalon.api.update_current_task(app="maya",
                                   task="model",
                                   asset="Fin")


@pytest.fixture
def task_maya_animate_S01():
    avalon.api.update_current_task(app="maya",
                                   task="animate",
                                   asset="S01")
