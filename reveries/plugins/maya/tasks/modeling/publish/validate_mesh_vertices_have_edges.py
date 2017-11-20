import re
import pyblish.api
from maya import cmds
from reveries.maya import action


class ValidateMeshVerticesHaveEdges(pyblish.api.InstancePlugin):
    """Validate meshes have only vertices that are connected by to edges.

    Maya can have invalid geometry with vertices that have no edges or
    faces connected to them.

    In Maya 2016 EXT 2 and later there's a command to fix this:
        `maya.cmds.polyClean(mesh, cleanVertices=True)

    In older versions of Maya it works to select the invalid vertices
    and merge the components.

    To find these invalid vertices select all vertices of the mesh
    that are visible in the viewport (drag to select), afterwards
    invert your selection (Ctrl + Shift + I). The remaining selection
    contains the invalid vertices.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.15
    actions = [action.SelectInvalidAction]
    hosts = ['maya']
    label = 'Mesh Vertices Have Edges'

    @classmethod
    def get_invalid(cls, instance):
        invalid = []

        meshes = cmds.ls(instance, type="mesh", long=True)
        for mesh in meshes:
            num_vertices = cmds.polyEvaluate(mesh, vertex=True)

            # Vertices from all edges
            edges = "%s.e[*]" % mesh
            vertices = cmds.polyListComponentConversion(edges, toVertex=True)
            num_vertices_from_edges = len_flattened(vertices)

            if num_vertices != num_vertices_from_edges:
                invalid.append(mesh)

        return invalid

    def process(self, instance):

        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' Meshes found in instance with vertices that "
                "have no edges:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid
                    )
                )
            )
            raise Exception("%s <Mesh Vertices Have Edges> Failed." % instance)

        self.log.info("%s <Mesh Vertices Have Edges> Passed." % instance)


def len_flattened(components):
    """Return the length of the list as if it was flattened.

    Maya will return consecutive components as a single entry
    when requesting with `maya.cmds.ls` without the `flatten`
    flag. Though enabling `flatten` on a large list (e.g. millions)
    will result in a slow result. This command will return the amount
    of entries in a non-flattened list by parsing the result with
    regex.

    Args:
        components (list): The non-flattened components.

    Returns:
        int: The amount of entries.

    """
    assert isinstance(components, (list, tuple))
    n = 0

    pattern = re.compile(r"\[(\d+):(\d+)\]")
    for c in components:
        match = pattern.search(c)
        if match:
            start, end = match.groups()
            n += int(end) - int(start) + 1
        else:
            n += 1
    return n
