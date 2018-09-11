
from pytest_bdd import scenario, given, when, then

import pytest
import os


@pytest.fixture
def pytestbdd_feature_base_dir():
    return os.path.join(os.getcwd(), "features")


@scenario("into_avalon.feature",
          "Launch <DCC_App> with Reveries pipeline implemented")
def test_app_startup():
    pass


@given("an environment that meets the Avalon's demand")
def step_minmum_environment_setup(minmum_environment_setup):
    pass


@when("I initiate Avalon")
def step_init_avalon(init_avalon):
    pass


@when("I create a project <PROJECT_NAME>")
def step_create_project(create_project):
    pass


@when("I set my task: <SILO> - <ASSET> - <TASK>")
def step_select_task(select_task_at_launcher):
    pass


APP_PROC = {"_": None}
SUCESS = ":installed:{version}"
FAILED = ":failed:"


@when("I launch <DCC_App>")
def step_launch_app(launcher_launchs_app, DCC_App):
    import avalon.api
    import reveries

    app = launcher_launchs_app

    reporter = "print({0!r} if is_installed else {1!r});".format(
        SUCESS.format(version=reveries.version), FAILED)

    VALIDATE_CMD = {
        "mayapy": [
            "-c",
            ("from maya import standalone; standalone.initialize();"
             "import reveries.maya;"
             "is_installed = reveries.maya.installed;" +
             reporter),
        ]
    }

    app_name = None
    for name in VALIDATE_CMD:
        if DCC_App.startswith(name):
            app_name = name

    app.config["args"] = VALIDATE_CMD[app_name]

    APP_PROC["_"] = app.process(avalon.api.Session.copy())


@then('<DCC_App> will be startup with Reveries pipeline')
def step_impl_then():
    import reveries

    popen = APP_PROC["_"]
    result = popen.communicate()[0].split()[-1]

    if result == SUCESS.format(version=reveries.version):
        return
    elif result == FAILED:
        raise AssertionError("Pipeline install failed.")
    else:
        raise RuntimeError("Unknown error. Result: {}".format(result))
