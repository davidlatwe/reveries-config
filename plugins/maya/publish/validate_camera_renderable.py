
import pyblish.api


class ValidateSingleRenderableCamera(pyblish.api.InstancePlugin):
    """Ensure the instance content only renderable camera
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Single Renderable Camera"
    families = [
        "reveries.imgseq",
    ]

    def process(self, instance):
        if len(instance.data["renderCam"]) == 0:
            raise Exception("No renderable camera.")

        if len(instance.data["renderCam"]) > 1:
            raise Exception("Can only have one renderable camera.")
