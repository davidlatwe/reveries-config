import pyblish.api
from reveries.maya import lib, action


class ValidateMeshNonZeroEdgeLength(pyblish.api.InstancePlugin):
    """Validate meshes don't have edges with a zero length.

    Based on Maya's polyCleanup 'Edges with zero length'.

    Note:
        This can be slow for high-res meshes.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.15
    actions = [action.SelectInvalidAction]
    hosts = ['maya']
    label = 'Mesh Edge Length Non Zero'

    __tolerance = 1e-5

    def process(self, instance):
        """Process all meshes"""
        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' Meshes found with zero edge length:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception(
                "%s <Mesh Edge Length Non Zero> Failed." % instance)

        self.log.info("%s <Mesh Edge Length Non Zero> Passed." % instance)

    @classmethod
    def get_invalid(cls, instance):
        """Return the invalid edges.
        Also see:
        http://help.autodesk.com/view/MAYAUL/2015/ENU/?guid=Mesh__Cleanup

        """

        meshes = instance.data["meshes"]
        if not meshes:
            return list()

        # Get all edges
        edges = ['{0}.e[*]'.format(node) for node in meshes]

        # Filter by constraint on edge length
        invalid = lib.polyConstraint(edges,
                                     t=0x8000,  # type=edge
                                     length=1,
                                     lengthbound=(0, cls.__tolerance))

        return invalid
