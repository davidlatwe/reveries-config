
import pyblish.api

from reveries import pipeline


class ValidateTimeline(pyblish.api.InstancePlugin):
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

    def process(self, instance):

        start_frame, end_frame, fps = pipeline.compose_timeline_data()

        context_data = instance.context.data
        start = context_data.get("startFrame")
        end = context_data.get("endFrame")
        scene_fps = context_data.get("fps")

        # Check if any of the values are present
        if any(value is None for value in (start, end)):
            raise ValueError("No time values for this instance. "
                             "(Missing `startFrame` or `endFrame`)")

        # yield warning if start/end frame are not consistent with the
        # settings on database.
        if start_frame != start or end_frame != end:
            self.log.warning("Start/End frame not consistent with project "
                             "settings.")

        # raise error if fps is not consistent with the settings on database.
        if int(scene_fps) != int(fps):
            msg = "FPS not consistent with project settings."
            self.log.error(msg)
            raise ValueError(msg)
