
import os
import pyblish.api
import avalon

from reveries.plugins import context_process


def is_in_workspace(path, workdir):
    """ Returns whether path is a subdirectory (or file) within workdir"""
    path = os.path.realpath(path)
    workdir = os.path.realpath(workdir)

    # If not on same drive
    if os.path.splitdrive(path)[0] != os.path.splitdrive(workdir)[0]:
        return False

    # Get 'relative path' (can contain ../ which means going up)
    relative = os.path.relpath(path, workdir)

    # Check if the path starts by going up, if so it's not a subdirectory. :)
    if relative.startswith(os.pardir) or relative == os.curdir:
        return False
    else:
        return True


class ValidateWorkfileInWorkspace(pyblish.api.InstancePlugin):
    """Validate the workfile is inside workspace"""

    order = pyblish.api.ValidatorOrder
    label = "Workfile In Workspace"
    families = [
        "reveries.animation",
        "reveries.pointcache",
        "reveries.imgseq",
    ]

    @context_process
    def process(self, context):

        current_making = context.data.get("currentMaking")
        if not current_making:
            raise RuntimeError("No workfile collected, this is a bug.")

        workdir = os.environ.get("AVALON_WORKDIR",
                                 avalon.Session.get("AVALON_WORKDIR"))
        if not workdir:
            raise RuntimeError("Workdir not defined, this is a bug.")

        if not is_in_workspace(current_making, workdir):
            raise RuntimeError("Workfile is not no server, "
                               "please save to network drive.")
