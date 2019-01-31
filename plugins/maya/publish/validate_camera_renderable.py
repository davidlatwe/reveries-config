
import pyblish.api


class ValidateRenderableCamera(pyblish.api.InstancePlugin):
    """Ensure the instance content only renderable camera
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Renderable Camera"
    families = [
        "reveries.imgseq.batchrender",
        "reveries.imgseq.turntable",
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        invalid = []

        cameras = cmds.ls(instance[:], type="camera", long=True)
        for cam in cameras:
            if cam not in instance.data["renderCam"]:
                invalid.append(cam)

        return invalid

    def process(self, instance):
        if len(instance.data["renderCam"]) == 0:
            raise Exception("No renderable camera.")

        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Camera not renderable.")
