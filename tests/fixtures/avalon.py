
import pytest
import os
import sys
import time
import shutil
import platform


def import_module(mod_name, file_path):
    if sys.version_info[0] == 2:
        import imp
        foo = imp.load_source(mod_name, file_path)

    else:
        if sys.version_info[1] < 5:
            from importlib.machinery import SourceFileLoader
            foo = SourceFileLoader(mod_name, file_path).load_module()

        else:
            import importlib.util
            spec = importlib.util.spec_from_file_location(mod_name, file_path)
            foo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(foo)

    return foo


@pytest.fixture(scope="session")
def minmum_environment_setup():

    _backup = os.environ.copy()
    os.environ = dict()  # clean environment

    PROJECT_ROOT = os.path.join(os.getcwd(), "projects")
    HOST_WORKDIR = _backup.get("HOST_WORKDIR", os.getcwd())
    HOST_APPEXEC = _backup.get("HOST_APPEXEC",
                               os.path.join(HOST_WORKDIR, "tests", "bin"))

    os.environ["AVALON_PROJECTS"] = PROJECT_ROOT
    os.environ["HOST_WORKDIR"] = HOST_WORKDIR
    os.environ["DOCKER_WORKDIR"] = _backup.get("DOCKER_WORKDIR", "")

    for key in ("AVALON_MONGO",
                "AVALON_DB",
                "PYBLISH_BASE",
                "PYBLISH_QML",
                "AVALON_CORE",
                "AVALON_LAUNCHER",
                "AVALON_SETUP",
                "AVALON_CONFIG"):
        os.environ[key] = _backup[key]

    os.environ["PYTHONPATH"] = os.pathsep.join([
        os.environ["HOST_WORKDIR"],  # config dir
    ])

    os.environ["PATH"] = os.pathsep.join([
        HOST_APPEXEC,
        _backup["AVALON_SETUP"],
    ])

    for name in ("LOGNAME", "USER", "LNAME", "USERNAME"):
        if _backup.get(name):
            os.environ[name] = _backup[name]

    if platform.system() == "Windows":
        os.environ["SYSTEMDRIVE"] = _backup["SYSTEMDRIVE"]
        os.environ["SYSTEMROOT"] = _backup["SYSTEMROOT"]
    os.environ["PATHEXT"] = _backup["PATHEXT"]  # This is a workaround

    # Avalon CLI environment assemble
    avalon_cli_path = os.path.join(_backup["AVALON_SETUP"], "avalon.py")
    avaon_cli = import_module("avaon_cli", avalon_cli_path)
    avaon_cli._install()

    yield

    # Teardown
    os.environ = _backup

    endtime = time.time() + 30
    while time.time() < endtime:
        # PROJECT_ROOT may still being used by other process
        # keep trying to delete it within 30 secs
        shutil.rmtree(PROJECT_ROOT, ignore_errors=True)
        if os.path.isdir(PROJECT_ROOT):
            time.sleep(1)
        else:
            break


@pytest.fixture
def init_avalon():
    import avalon.io

    # Init Avalon session, connect database
    avalon.io.install()

    yield

    avalon.io.uninstall()


@pytest.fixture
def create_project(PROJECT_NAME):
    import avalon.api
    import avalon.io
    import avalon.inventory

    avalon.api.Session["AVALON_PROJECT"] = PROJECT_NAME

    # Ensure clean project collection for test
    avalon.io.drop()

    # Write data
    PROJECT_ROOT = os.environ["AVALON_PROJECTS"]
    PROJECT_PATH = os.path.join(PROJECT_ROOT, PROJECT_NAME)
    os.makedirs(PROJECT_PATH)
    data = _project_data(PROJECT_PATH)
    avalon.inventory.save(PROJECT_NAME, *data)

    yield

    # Teardown
    avalon.io.drop()


def _project_data(PROJECT_PATH):
    import avalon.vendor

    CONFIG_TOML = os.path.join(PROJECT_PATH, ".config.toml")
    INVENT_TOML = os.path.join(PROJECT_PATH, ".inventory.toml")

    shutil.copyfile("res/.config.toml", CONFIG_TOML)
    shutil.copyfile("res/.inventory.toml", INVENT_TOML)

    def _load_toml(fname):
        with open(fname) as f:
            data = avalon.vendor.toml.load(f)
        return data

    config = _load_toml(CONFIG_TOML)
    inventory = _load_toml(INVENT_TOML)

    return config, inventory


@pytest.fixture
def select_task_at_launcher(SILO, ASSET, TASK):
    import avalon.api

    avalon.api.Session["AVALON_SILO"] = SILO
    avalon.api.Session["AVALON_ASSET"] = ASSET
    avalon.api.Session["AVALON_TASK"] = TASK


@pytest.fixture
def launcher_launchs_app(DCC_App):
    import avalon.api
    import avalon.io
    import avalon.lib

    project_data = avalon.io.find_one({"type": "project"})

    # Launcher finding App
    Action = None
    for app in project_data["config"]["apps"]:
        if not app["name"] == DCC_App:
            continue

        app_definition = avalon.lib.get_application(DCC_App)

        Action = type(
            "app_%s" % DCC_App,
            (avalon.api.Application,),
            {
                "name": DCC_App,
                "config": app_definition.copy()
            }
        )

        if Action().is_compatible(avalon.api.Session):
            break

    assert Action, "No action found"

    return Action()


@pytest.fixture
def change_task(task, asset):
    import avalon.api
    avalon.api.update_current_task(task=task, asset=asset)
