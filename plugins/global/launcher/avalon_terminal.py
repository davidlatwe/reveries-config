
import os
import sys
from avalon import (
    api,
    io,
    lib,
    pipeline,
)
from avalon.vendor import six


class Terminal(api.Application):

    name = "terminal"
    label = "Terminal"
    icon = "terminal"
    color = "#7F8C9B"
    order = 10

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_PROJECTS" in session:
            return True
        return False

    def is_workdir_compatible(self, session):
        required = ["AVALON_PROJECTS",
                    "AVALON_PROJECT",
                    "AVALON_SILO",
                    "AVALON_ASSET",
                    "AVALON_TASK",
                    "AVALON_APP"]
        missing = [x for x in required
                   if session.get(x) in (None, "placeholder")]
        if missing:
            print("Missing keys for workdir: %s" % (missing,))
            return False
        return True

    def environ(self, session):
        """Build application environment"""

        project = io.find_one({"type": "project"})
        if project is not None:

            template = project["config"]["template"]["work"]

            if self.is_workdir_compatible(session):
                # Compute work directory
                workdir = pipeline._format_work_template(template, session)
                session["AVALON_WORKDIR"] = workdir
                session["AVALON_SHELL_CWD"] = workdir
                if not os.path.isdir(workdir):
                    os.makedirs(workdir)
            else:
                # Compute cwd as far as we can
                workdir = pipeline._format_work_template(template, session)
                parts = workdir.split("/")
                cwd = ""
                for p in parts:
                    _cwd = os.path.join(cwd, p)
                    if not os.path.isdir(_cwd):
                        break
                    cwd = _cwd
                session["AVALON_SHELL_CWD"] = cwd

        # Construct application environment from .toml config (app_definition)
        app_environment = self.config.get("environment", {})
        for key, value in app_environment.copy().items():
            if isinstance(value, list):
                # Treat list values as paths, e.g. PYTHONPATH=[]
                app_environment[key] = os.pathsep.join(value)

            elif isinstance(value, six.string_types):
                if lib.PY2:
                    # Protect against unicode in the environment
                    encoding = sys.getfilesystemencoding()
                    app_environment[key] = value.encode(encoding)
                else:
                    app_environment[key] = value
            else:
                print(
                    "%s: Unsupported environment reference in %s for %s"
                    % (value, self.name, key)
                )

        # Build environment
        env = os.environ.copy()
        env.update(session)
        app_environment = self._format(app_environment, **env)
        env.update(app_environment)

        return env

    def process(self, session, **kwargs):
        """Implement the behavior for when the action is triggered

        Args:
            session (dict): environment dictionary

        Returns:
            Popen instance of newly spawned process

        """
        APP = "shell"

        app_definition = lib.get_application(APP)
        self.config = app_definition

        session = session.copy()
        session["AVALON_APP"] = APP
        session["AVALON_APP_NAME"] = self.name

        env = self.environ(session)

        # Get executable by name
        executable = lib.which(self.config["executable"])

        #
        # (NOTE): The result CWD path may not be accurate since the
        #         Launcher did not clean up the entry while changing
        #         frames.
        #         For example:
        #             if you were in 'ProjA > Char > Boy > modeling'
        #             and jump to 'ProjB > Prop' then launch action,
        #             you will find the CWD path is:
        #                 'ProjB > Prop > Boy > modeling'
        #             not just:
        #                 'ProjB > Prop'
        #
        cwd = env.get("AVALON_SHELL_CWD", session.get("AVALON_PROJECTS", ""))

        if cwd and not os.path.isdir(cwd):
            self.log.error("The path of `cwd` is not a directory: "
                           "{!r}".format(cwd))
            cwd = None

        return lib.launch(executable=executable,
                          args=[],
                          environment=env,
                          cwd=cwd)
