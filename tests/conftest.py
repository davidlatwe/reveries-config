
import os

from .fixtures.avalon import (
    minmum_environment_setup,
    init_avalon,
    create_project,
    select_task_at_launcher,
    launcher_launchs_app,
    change_task,
)


__all__ = [
    "minmum_environment_setup",
    "init_avalon",
    "create_project",
    "select_task_at_launcher",
    "launcher_launchs_app",
    "change_task",
]


collect_ignore = []

if not os.environ.get("REVERIES_IN_HOUSE_TEST"):
    collect_ignore.append("pkg/module_py2.py")
