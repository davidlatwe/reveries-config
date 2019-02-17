
import getpass
from avalon import api, lib, io


class ProjectManagerAction(api.Action):
    """Only project admin can access
    """
    name = "projectmanager"
    label = "Project Manager"
    icon = "gear"
    color = "#767676"
    order = 999     # at the end

    def is_compatible(self, session):
        project = io.find_one({"type": "project"},
                              projection={"data.role.admin": True})

        if project is not None:
            user = getpass.getuser().lower()
            admin = project["data"].get("role", {}).get("admin", [user])

            if user not in admin:
                return False

        return "AVALON_PROJECT" in session

    def process(self, session, **kwargs):
        return lib.launch(executable="python",
                          args=["-u", "-m", "avalon.tools.projectmanager",
                                session['AVALON_PROJECT']])
