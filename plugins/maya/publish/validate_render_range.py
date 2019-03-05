
import pyblish.api
from reveries.maya import pipeline
from reveries import utils


class ValidateRenderRange(pyblish.api.InstancePlugin):
    """Ensure render setttings has been set correctly

        This plugin validate the rendering range (strict)

    """

    label = "Render Range"
    order = pyblish.api.ValidatorOrder + 0.2
    hosts = ["maya"]
    families = [
        "reveries.imgseq.render",
        "reveries.imgseq.lookdev",
    ]

    @classmethod
    def get_invalid(cls, instance):
        """Rendering range should be the same as pre-defined range"""
        project = instance.context.data["projectDoc"]
        asset_name = pipeline.has_turntable()
        proj_start, proj_end, _ = utils.compose_timeline_data(project,
                                                              asset_name)
        render_start = instance.data["startFrame"]
        render_end = instance.data["endFrame"]

        if proj_start != render_start or proj_end != render_end:
            cls.log.error("start and end frame should be {0} - {1}."
                          "".format(proj_start, proj_end))
            return True

    def process(self, instance):
        self.log.info("Validating frame range..")
        if self.get_invalid(instance):
            raise Exception("Rendering frame range is not correct.")

    @classmethod
    def fix_invalid(cls, instance):
        NotImplemented
