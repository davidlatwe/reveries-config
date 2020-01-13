
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

    # (TODO) If it's on the same drive, it's good for now.
    #        Currently some artist may open others workfile and publish,
    #        this should not be allowed in future.
    return True

    # Get 'relative path' (can contain ../ which means going up)
    relative = os.path.relpath(path, workdir)

    # Check if the path starts by going up, if so it's not a subdirectory. :)
    if relative.startswith(os.pardir) or relative == os.curdir:
        return False
    else:
        return True


class ValidateWorkfileInWorkspace(pyblish.api.InstancePlugin):
    """確認工作檔確實存檔於 Avalon 的工作區"""

    """Validate the workfile is inside workspace"""

    order = pyblish.api.ValidatorOrder - 0.49995
    label = "確認工作檔存在於工作區"
    families = [
        "reveries.pointcache",
        "reveries.renderlayer",
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
            raise RuntimeError("工作檔不存在於工作區，請將工作檔另存至工作區。")
