
import pyblish.api
from reveries.maya import utils as maya_utils
from reveries.maya import pipeline
from reveries import utils


class ValidateRenderResolution(pyblish.api.InstancePlugin):
    """Ensure render setttings has been set correctly

        This plugin validate the render resolution

    """

    label = "Render Resolution"
    order = pyblish.api.ValidatorOrder + 0.2
    hosts = ["maya"]
    families = [
        "reveries.imgseq.render",
        "reveries.imgseq.lookdev",
    ]

    @classmethod
    def get_invalid(cls, instance):
        """Rendering resolution should be the same as project settings"""
        project = instance.context.data["projectDoc"]
        asset_name = pipeline.has_turntable()
        proj_width, proj_height = utils.get_resolution_data(project,
                                                            asset_name)
        layer = instance.data["renderlayer"]
        scene_width, scene_height = maya_utils.get_render_resolution(layer)

        if proj_width != scene_width or proj_height != scene_height:
            cls.log.error("Resolution width and height should be {0} x {1}."
                          "".format(proj_width, proj_height))
            return True

    def process(self, instance):
        self.log.info("Validating image resolution..")
        if self.get_invalid(instance):
            raise Exception("Rendering resolution is not correct.")

    @classmethod
    def fix_invalid(cls, instance):
        NotImplemented
