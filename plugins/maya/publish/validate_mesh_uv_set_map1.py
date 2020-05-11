
import pyblish.api
from reveries import plugins


class ValidateMeshUVSetMap1(pyblish.api.InstancePlugin):
    """Validate model's default set exists and is named 'map1'.

    In Maya meshes by default have a uv set named "map1" that cannot be
    deleted. It can be renamed however, introducing some issues with some
    renderers. As such we ensure the first (default) UV set index is named
    "map1".

    """

    order = pyblish.api.ValidatorOrder + 0.22
    hosts = ["maya"]
    families = ["reveries.model"]
    label = "Mesh has map1 UV Set"
    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
        pyblish.api.Category("Fix It"),
        plugins.RepairInstanceAction,
    ]

    @staticmethod
    def get_invalid(instance):
        from maya import cmds

        meshes = cmds.ls(instance, type="mesh", noIntermediate=True)

        invalid = []
        for mesh in meshes:

            # Get existing mapping of uv sets by index
            indices = cmds.polyUVSet(mesh, query=True, allUVSetsIndices=True)
            maps = cmds.polyUVSet(mesh, query=True, allUVSets=True)
            mapping = dict(zip(indices, maps))

            # Get the uv set at index zero.
            name = mapping[0]
            if name != "map1":
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Meshes found without 'map1' "
                             "UV set: {0}".format(invalid))

    @classmethod
    def fix_invalid(cls, instance):
        """Rename uv map at index zero to map1"""
        from maya import cmds

        def rename_uvset(mesh, original, newname):
            try:
                cmds.polyUVSet(mesh,
                               rename=True,
                               uvSet=original,
                               newUVSet=newname)
            except RuntimeError:
                cls.log.error("Mesh '%s' UVSet '%s' cannot be renamed."
                              % (mesh, original))

        for mesh in cls.get_invalid(instance):

            # Get existing mapping of uv sets by index
            indices = cmds.polyUVSet(mesh, query=True, allUVSetsIndices=True)
            maps = cmds.polyUVSet(mesh, query=True, allUVSets=True)
            mapping = dict(zip(indices, maps))

            # Ensure there is no uv set named map1 to avoid
            # a clash on renaming the "default uv set" to map1
            existing = set(maps)
            if "map1" in existing:

                # Find a unique name index
                i = 2
                while True:
                    name = "map{0}".format(i)
                    if name not in existing:
                        break
                    i += 1

                cls.log.warning("Renaming clashing uv set name on mesh"
                                " %s to '%s'", mesh, name)

                rename_uvset(mesh, "map1", name)

            # Rename the initial index to map1
            original = mapping[0]
            rename_uvset(mesh, original, "map1")
