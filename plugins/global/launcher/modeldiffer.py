
import os
from avalon import api, lib


class ModeldifferAction(api.Action):
    """
    """
    name = "modeldiffer"
    label = "Model Differ"
    icon = "share-alt-square"
    color = "#EC905C"
    order = 999     # at the end

    def is_compatible(self, session):
        required = ["AVALON_PROJECTS",
                    "AVALON_PROJECT"]
        missing = [x for x in required
                   if session.get(x) in (None, "placeholder")]

        return not missing

    def process(self, session, **kwargs):
        environ = os.environ.copy()
        environ.update(session)

        if environ.get("AVALON_SILO") == "placeholder":
            environ["AVALON_SILO"] = ""
        if environ.get("AVALON_ASSET") == "placeholder":
            environ["AVALON_ASSET"] = ""

        return lib.launch(executable="python",
                          args=["-u", "-m", "reveries.tools.modeldiffer"],
                          environment=environ)
