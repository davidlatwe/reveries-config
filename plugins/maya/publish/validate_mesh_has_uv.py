
import re
from maya import cmds

import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectNoUV(MayaSelectInvalidInstanceAction):

    label = "Empty UV"
    on = "failed"
    icon = "frown-o"

    symptom = "no_uv"


class SelectIncompleteUV(MayaSelectInvalidInstanceAction):

    label = "Incomplete UV"
    on = "failed"
    icon = "meh-o"

    symptom = "incomplete_uv"


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
    for c in components:
        match = re.search("\[([0-9]+):([0-9]+)\]", c)
        if match:
            start, end = match.groups()
            n += int(end) - int(start) + 1
        else:
            n += 1
    return n


class ValidateMeshHasUVs(pyblish.api.InstancePlugin):
    """Validate the current mesh has UVs.

    It validates whether the current UV set has non-zero UVs and
    at least more than the vertex count. It's not really bulletproof,
    but a simple quick validation to check if there are likely
    UVs for every face.

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Mesh Has UVs"
    families = [
        "reveries.model",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectNoUV,
        SelectIncompleteUV,
    ]

    @classmethod
    def get_invalid_no_uv(cls, instance):
        invalid = []

        for node in cmds.ls(instance, type="mesh"):
            uv = cmds.polyEvaluate(node, uv=True)

            if uv == 0:
                invalid.append(node)

        return invalid

    @classmethod
    def get_invalid_incomplete_uv(cls, instance):
        invalid = []

        for node in cmds.ls(instance, type="mesh"):
            uv = cmds.polyEvaluate(node, uv=True)

            vertex = cmds.polyEvaluate(node, vertex=True)
            if uv > 0 and uv < vertex:
                # Workaround:
                # Maya can have instanced UVs in a single mesh, for example
                # imported from an Alembic. With instanced UVs the UV count
                # from `maya.cmds.polyEvaluate(uv=True)` will only result in
                # the unique UV count instead of for all vertices.
                #
                # Note: Maya can save instanced UVs to `mayaAscii` but cannot
                #       load this as instanced. So saving, opening and saving
                #       again will lose this information.
                map_attr = "{}.map[*]".format(node)
                uv_to_vertex = cmds.polyListComponentConversion(map_attr,
                                                                toVertex=True)
                uv_vertex_count = len_flattened(uv_to_vertex)
                if uv_vertex_count < vertex:
                    invalid.append(node)
                else:
                    cls.log.warning("Node has instanced UV points: "
                                    "{0}".format(node))

        return invalid

    def process(self, instance):

        no_uv = self.get_invalid_no_uv(instance)
        incomplete_uv = self.get_invalid_incomplete_uv(instance)

        if no_uv or incomplete_uv:
            raise RuntimeError("Meshes found in instance without "
                               "valid UVs: {0}".format(instance))
