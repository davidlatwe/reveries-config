import pyblish.api
from reveries.maya import action


class ValidateMeshMaxUVSetsCount(pyblish.api.InstancePlugin):
    """Ensure UV sets count in each polygon mesh does not exceed the limitation
    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.2
    actions = [action.SelectInvalidAction]
    hosts = ['maya']
    label = "Mesh Max UV Sets Count"

    @staticmethod
    def get_invalid(instance, max_uv_sets_count):

        model_uvSet_state = instance.data["model_uvSet_state"]

        invalid = list()
        for mesh in model_uvSet_state:
            if len(model_uvSet_state[mesh]) > max_uv_sets_count:
                invalid.append(mesh)
        return invalid

    def process(self, instance):
        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        max_uv_sets_count = instance.data["max_uv_sets_count"]
        invalid = self.get_invalid(instance, max_uv_sets_count)

        if invalid:
            self.log.error(
                "'%s' UV sets exceeded. Limitation %s. Invalid Mesh:\n%s" % (
                    instance,
                    max_uv_sets_count,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Mesh Max UV Sets Count> Failed." % instance)

        self.log.info("%s <Mesh Max UV Sets Count> Passed." % instance)
