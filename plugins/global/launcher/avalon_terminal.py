
import os
import avalon


class FusionRenderNode(avalon.api.Action):

    name = "terminal"
    label = "Terminal"
    icon = "terminal"

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_PROJECTS" in session:
            return True
        return False

    def process(self, session, **kwargs):
        """Implement the behavior for when the action is triggered

        Args:
            session (dict): environment dictionary

        Returns:
            Popen instance of newly spawned process

        """

        # Update environment with session
        env = os.environ.copy()
        env.update(session)

        # Get executable by name
        app = avalon.lib.get_application("shell")
        env.update(app["environment"])
        executable = avalon.lib.which(app["executable"])

        return avalon.lib.launch(executable=executable,
                                 args=[],
                                 environment=env,
                                 cwd=session["AVALON_PROJECTS"])
