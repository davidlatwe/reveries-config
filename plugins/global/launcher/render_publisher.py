
import os
from avalon import api, lib


class RenderPublisherAction(api.Action):
    """
    """
    name = "renderpublisher"
    label = "Render Publisher"
    icon = "film"
    color = "#66AC5C"
    order = 900

    def is_compatible(self, session):
        required = ["AVALON_PROJECTS",
                    "AVALON_PROJECT",
                    "AVALON_SILO",
                    "AVALON_ASSET",
                    "AVALON_TASK"]
        missing = [x for x in required
                   if session.get(x) in (None, "placeholder")]

        return not missing

    def process(self, session, **kwargs):
        from reveries import filesys

        environ = os.environ.copy()
        environ.update(session)

        app = filesys.Filesys()
        env = app.environ(session)
        environ["AVALON_WORKDIR"] = env["AVALON_WORKDIR"].replace("\\", "/")

        return lib.launch(executable="python",
                          args=[
                              "-m",
                              "reveries.tools.seqparser",
                              "--publish",
                          ],
                          environment=environ)
