
import pyblish.api

from reveries import utils
from reveries.maya.lib import set_scene_timeline
from reveries.plugins import RepairContextAction


class RepairInvalid(RepairContextAction):

    label = "Reset Timeline"


class ValidateTimeline(pyblish.api.ContextPlugin):
    """Valides the frame ranges and fps.
    """

    label = "Validate Timeline"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = [
        "reveries.animation",
        "reveries.pointcache",
        "reveries.camera",
        "reveries.playblast",
    ]
    actions = [
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    def process(self, context):

        project = context.data["projectDoc"]
        start_frame, end_frame, fps = utils.compose_timeline_data(project)

        start = context.data.get("startFrame")
        end = context.data.get("endFrame")
        scene_fps = context.data.get("fps")

        # Check if any of the values are present
        if any(value is None for value in (start, end)):
            raise ValueError("No time values for this context. This is a bug."
                             "(Missing `startFrame` or `endFrame`)")

        is_invalid = False
        # raise error if start/end frame are not consistent with the
        # settings on database.
        if start_frame != start or end_frame != end:
            is_invalid = True
            self.log.error("Start/End frame not consistent with project "
                           "settings.")

        # raise error if fps is not consistent with the settings on database.
        if int(scene_fps) != int(fps):
            is_invalid = True
            self.log.error("FPS not consistent with project settings.")

        if is_invalid:
            raise ValueError("Timeline does not match with project settings.")

    @classmethod
    def fix(cls, context):
        set_scene_timeline()
