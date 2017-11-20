import pyblish.api
from reveries.maya import action


class ValidateMeshNoRedundantUVSet(pyblish.api.InstancePlugin):
    """Ensure No Redundant UV set exist for each polygon mesh

    Except default UV set, not allow other empty/invalid UV set.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.2
    actions = [action.SelectInvalidAction]
    hosts = ['maya']
    label = "Mesh No Redundant UV Set"

    @staticmethod
    def get_invalid(instance):

        model_uvSet_state = instance.data["model_uvSet_state"]

        invalid = []
        for mesh in model_uvSet_state:
            uv_set_state = model_uvSet_state[mesh]
            if any(uv_set_state) and uv_set_state.count(False) > 0:
                invalid.append(mesh)
            if not any(uv_set_state) and uv_set_state.count(False) > 1:
                invalid.append(mesh)
        return invalid

    def process(self, instance):
        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")
        self.log.info(instance.data["model_uvSet_state"])

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' Meshes found redundant UV sets:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Mesh No Redundant UV Set> Failed." % instance)

        self.log.info("%s <Mesh No Redundant UV Set> Passed." % instance)
