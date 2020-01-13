
import pyblish.api
from reveries.maya import utils as maya_utils


class ValidateRenderFileExtension(pyblish.api.InstancePlugin):
    """Ensure render setttings has been set correctly

        This plugin validate the file name extension

    """

    label = "Render File Extension"
    order = pyblish.api.ValidatorOrder + 0.2
    hosts = ["maya"]
    families = [
        "reveries.renderlayer",
    ]

    extensions = ("exr", "deepexr", "png", "tif", "jpg", "jpeg")

    @classmethod
    def get_invalid(cls, instance):
        layer = instance.data["renderlayer"]
        filename = maya_utils.compose_render_filename(layer)
        cls.log.debug("Composed file name: %s" % filename)

        ext = filename.rsplit(".", 1)[-1]

        if ext not in cls.extensions:
            cls.log.error("File extension should be set to one of {}."
                          "".format(cls.extensions))
            return True

    def process(self, instance):
        self.log.info("Validating file extension..")
        if self.get_invalid(instance):
            raise Exception("Render output extension invalid.")
