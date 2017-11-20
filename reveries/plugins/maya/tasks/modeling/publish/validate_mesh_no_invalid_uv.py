import pyblish.api
from reveries.maya import action


class ValidateMeshNoInvalidUV(pyblish.api.InstancePlugin):
    """Emit Warning If No Invalid UV in each polygon mesh and each UV sets"""

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.3
    actions = [action.SelectInvalidAction]
    hosts = ['maya']
    label = "Mesh No Invalid UV"

    @staticmethod
    def get_invalid(instance):

        model_uvSet_state = instance.data["model_uvSet_state"]

        invalid = []
        for mesh in model_uvSet_state:
            if not all(model_uvSet_state[mesh]):
                invalid.append(mesh)
        return invalid

    def process(self, instance):
        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.warning(
                "'%s' Meshes found Invalid UV. Invalid Mesh:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            self.log.warning("%s <Mesh No Invalid UV> Warned." % instance)
        else:
            self.log.info("%s <Mesh No Invalid UV> Passed." % instance)
