
import pyblish.api

from reveries import utils
from reveries.maya.lib import set_scene_timeline
from reveries.plugins import RepairContextAction, context_process


class RepairInvalid(RepairContextAction):

    label = "Reset Timeline"


class ValidateTimeline(pyblish.api.InstancePlugin):
    """Valides the frame ranges and fps.

    * FPS must have same settings with the value defined in project document.

    * Frame range will be fine as long as the timeline in scene is wider
      than the range defined in project document.

    """

    label = "Validate Timeline"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = [
        "reveries.animation",
        "reveries.pointcache",
        "reveries.camera",
        "reveries.imgseq",
    ]
    actions = [
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    @context_process
    def process(self, context):

        asset_name = self.swap_to_turntable_if_there_is_one(context)

        project = context.data["projectDoc"]
        proj_start, proj_end, fps = utils.compose_timeline_data(project,
                                                                asset_name)

        scene_start = context.data.get("startFrame")
        scene_end = context.data.get("endFrame")
        scene_fps = context.data.get("fps")

        # Check if any of the values are present
        if any(value is None for value in (scene_start, scene_end)):
            raise ValueError("No time values for this context. This is a bug."
                             "(Missing `startFrame` or `endFrame`)")

        is_invalid = False
        # Raise error if scene_start/scene_end are not enough to include the
        # frame range settings in database.
        if proj_start > scene_start or proj_end < scene_end:
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
    def swap_to_turntable_if_there_is_one(cls, context):
        for instance in context:
            families = instance.data.get("families", [])

            if "reveries.imgseq.turntable" in families:
                cls.log.info("Get timeline data from turntable.")

                # (NOTE) The turntable asset name is hardcoded here,
                #        better not to do this.
                return "LookDevStage"

    @classmethod
    def fix(cls, context):
        asset_name = cls.swap_to_turntable_if_there_is_one(context)
        strict = False if asset_name is None else True
        set_scene_timeline(asset_name=asset_name, strict=strict)
