
import os
from avalon import (
    api,
    io,
    lib,
    pipeline,
)


class Terminal(api.Action):

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
            print("Missing keys: %s" % (missing,))
            return False
        return True

    def environ(self, session):
        """Build application environment"""

        session = session.copy()
        session["AVALON_APP"] = "shell"
        session["AVALON_APP_NAME"] = self.name

        # Compute work directory
        if self.is_workdir_compatible(session):
            project = io.find_one({"type": "project"})
            template = project["config"]["template"]["work"]
            workdir = pipeline._format_work_template(template, session)
            session["AVALON_WORKDIR"] = workdir

        # Build environment
        env = os.environ.copy()
        env.update(session)

        return env

    def process(self, session, **kwargs):
        """Implement the behavior for when the action is triggered

        Args:
            session (dict): environment dictionary

        Returns:
            Popen instance of newly spawned process

        """
        env = self.environ(session)

        # Get executable by name
        app = lib.get_application("shell")
        env.update(app["environment"])
        executable = lib.which(app["executable"])

        return lib.launch(executable=executable,
                          args=[],
                          environment=env,
                          cwd=session["AVALON_PROJECTS"])
