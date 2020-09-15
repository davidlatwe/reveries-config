
import os
from avalon import api, lib, io


class USDSetGroup(api.Action):
    """
    """
    name = "usd_set_group"
    label = "USD Set Group"

    icon = "group"
    color = "#1590fb"
    order = 999     # at the end

    def is_compatible(self, session):
        required = ["AVALON_PROJECTS",
                    "AVALON_PROJECT"]
        missing = [x for x in required
                   if session.get(x) in (None, "placeholder")]

        # Use USD pipeline
        project = io.find_one({"name": session.get("AVALON_PROJECT"), "type": "project"})
        if project:
            if not project.get('usd_pipeline', False):
                missing = True

        return not missing

    def process(self, session, **kwargs):
        environ = os.environ.copy()
        environ.update(session)

        if environ.get("AVALON_SILO") == "placeholder":
            environ["AVALON_SILO"] = ""
        if environ.get("AVALON_ASSET") == "placeholder":
            environ["AVALON_ASSET"] = ""

        return lib.launch(executable="python",
                          args=["-u", "-m", "reveries.tools.usd_set_group"],
                          environment=environ)
