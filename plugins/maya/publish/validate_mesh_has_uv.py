
import pyblish.api
from reveries import plugins


class SelectNoUV(plugins.MayaSelectInvalidInstanceAction):

    label = "Empty UV"
    on = "failed"
    icon = "frown-o"

    symptom = "no_uv"


class ValidateMeshHasUVs(pyblish.api.InstancePlugin):
    """Validate the current mesh has UVs.

    It validates whether the current UV set has non-zero UVs and
    at least more than the vertex count. It's not really bulletproof,
    but a simple quick validation to check if there are likely
    UVs for every face.

    """

    order = pyblish.api.ValidatorOrder + 0.2
    hosts = ["maya"]
    label = "Mesh Has UVs"
    families = [
        "reveries.model",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectNoUV,
    ]

    optional = True  # (NOTE) Forced by artist complain

    @classmethod
    def get_invalid_no_uv(cls, instance):
        from maya import cmds

        invalid = []

        for node in cmds.ls(instance, type="mesh", noIntermediate=True):
            uv = cmds.polyEvaluate(node, uv=True)

            if uv == 0:
                invalid.append(node)

        return invalid

    def process(self, instance):
        no_uv = self.get_invalid_no_uv(instance)
        if no_uv:
            raise RuntimeError("Meshes found in instance without "
                               "valid UVs: {0}".format(instance))
