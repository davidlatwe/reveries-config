
import pyblish.api
from reveries import plugins


class RepairInvalid(plugins.RepairContextAction):

    label = "Reset Timeline"


def asset_has_frame_range(context):
    def has_edit_in(instance):
        return "edit_in" in instance.data["assetDoc"]["data"]
    # (TODO) Shouldn't be refactored like this..
    #   But sufficed for now. (Moving `assetDoc` from context to instance)
    return any(has_edit_in(instance) for instance in context)


class ValidateTimeline(pyblish.api.InstancePlugin):
    """Validate frame ranges and fps.

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
        "reveries.atomscrowd",
    ]
    actions = [
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    @plugins.context_process
    def process(self, context):
        from reveries import utils
        from reveries.maya import pipeline

        # (TODO) Involving turntable is because this plugin used to validate
        #   dailies turntable playblast or render publishing.
        #   But we don't do it here now, should be removed.
        asset_name = pipeline.has_turntable()

        if asset_name is None and not asset_has_frame_range(context):
            self.log.info("No range been set on this asset, skipping..")
            return True

        # (TODO) Might need to get frame data from instance object, for case
        #   like publishing multiple shots' camera in one scene.
        scene_start = context.data["startFrame"]
        scene_end = context.data["endFrame"]
        scene_fps = context.data["fps"]

        project = context.data["projectDoc"]
        proj_start, proj_end, fps = utils.compose_timeline_data(project,
                                                                asset_name,
                                                                scene_fps)

        # Check if any of the values are present
        if any(value is None for value in (scene_start, scene_end)):
            raise ValueError("No time values for this context. This is a bug."
                             "(Missing `startFrame` or `endFrame`)")

        is_invalid = False
        # Raise error if scene_start/scene_end are not enough to include the
        # frame range settings in database.
        if proj_start < scene_start:
            is_invalid = True
            self.log.debug("Start Frame: {}".format(proj_start))
            self.log.debug("Scene Start Frame: {}".format(scene_start))
            self.log.error("Start frame not consistent with project "
                           "settings.")
        if proj_end > scene_end:
            is_invalid = True
            self.log.debug("End Frame: {}".format(proj_end))
            self.log.debug("Scene End Frame: {}".format(scene_end))
            self.log.error("End frame not consistent with project "
                           "settings.")

        # raise error if fps is not consistent with the settings on database.
        if int(scene_fps) != int(fps):
            is_invalid = True
            self.log.debug("FPS: {}".format(fps))
            self.log.debug("Scene FPS: {}".format(scene_fps))
            self.log.error("FPS not consistent with project settings.")

        if is_invalid:
            raise ValueError("Timeline does not match with project settings.")

    @classmethod
    def fix_invalid(cls, context):
        from reveries.maya import pipeline

        asset_name = pipeline.has_turntable()
        strict = False if asset_name is None else True
        pipeline.set_scene_timeline(asset_name=asset_name, strict=strict)
