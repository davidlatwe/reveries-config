
from avalon import api, lib


class ProjectMemberAction(api.Action):

    name = "projectmember"
    label = "Favorites"
    icon = "heart"
    color = "#E74C3C"
    order = 999     # at the end

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        return "AVALON_PROJECTS" in session and "AVALON_PROJECT" not in session

    def process(self, session, **kwargs):
        return lib.launch(executable="python",
                          args=["-u", "-m", "reveries.tools.projectmember"])
