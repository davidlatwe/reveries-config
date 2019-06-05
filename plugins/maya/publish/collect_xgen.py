
import pyblish.api
from maya import cmds
from reveries import plugins
from reveries.maya import lib, xgen, pipeline


def create_model_subset_from_xgen(instance):
    family = "reveries.model"
    subset = instance.data["subset"]
    subset = "model" + subset[0].upper() + subset[1:]

    if "igsBoundMeshes" in instance.data:
        member = cmds.listRelatives(instance.data["igsBoundMeshes"],
                                    allParents=True,
                                    fullPath=True) or []
    if "xgenBoundGeos" in instance.data:
        member = instance.data["xgenBoundGeos"]

    member += lib.list_all_parents(member)
    if member:
        model = plugins.create_dependency_instance(instance,
                                                   subset,
                                                   family,
                                                   member,
                                                   category="XGen Bound Mesh")
        # Only need to extract model `mayaBinary` representation
        model.data["extractType"] = "mayaBinary"
        return True

    return False


def create_texture_subset_from_xgen(instance, textures):
    family = "reveries.texture"
    subset = instance.data["subset"]
    subset = "texture" + subset[0].upper() + subset[1:]
    plugins.create_dependency_instance(instance,
                                       subset,
                                       family,
                                       textures,
                                       category="XGen Maps")


class CollectXGen(pyblish.api.InstancePlugin):
    """Collect xgen content and data
    """

    order = pyblish.api.CollectorOrder + 0.1  # run before look collector
    hosts = ["maya"]
    label = "Collect XGen"
    families = ["reveries.xgen"]

    def process(self, instance):
        getattr(self, "get_" + instance.data["XGenType"])(instance)

    def get_interactive(self, instance):
        """Interactive Groom Spline"""

        descriptions = xgen.interactive.list_lead_descriptions(instance[:])
        instance.data["igsDescriptions"] = descriptions

        bound_meshes = set()
        for desc in descriptions:
            bound_meshes.update(xgen.interactive.list_bound_meshes(desc))
        instance.data["igsBoundMeshes"] = list(bound_meshes)

        # Create model subset for bounding meshes
        result = create_model_subset_from_xgen(instance)
        if not result:
            self.log.warning("No bound mesh been found.")

        # Create texture subet for descriptions
        stray = pipeline.find_stray_textures(cmds.listHistory(descriptions))
        if stray:
            create_texture_subset_from_xgen(instance, stray)

    def get_legacy(self, instance):
        """Legacy XGen"""

        palettes = []
        palette_nodes = cmds.ls(instance, type="xgmPalette", long=True)
        for palette in xgen.legacy.list_palettes():
            if any(n in palette_nodes for n in cmds.ls(palette, long=True)):
                palettes.append(palette)

        instance.data["xgenPalettes"] = palettes

        descriptions = list()
        for palette in palettes:
            descriptions += xgen.legacy.list_descriptions(palette)

        instance.data["xgenDescriptions"] = descriptions

        bound_meshes = set()
        for desc in descriptions:
            bound_meshes.update(xgen.legacy.list_bound_geometry(desc))
        instance.data["xgenBoundGeos"] = list(bound_meshes)

        # Update subset name with step
        name = instance.data["subset"]
        step = instance.data["step"]
        if step != xgen.legacy.SHAPING and not name.endswith(step):
            instance.data["subset"] = name + step

        # Create model subset for bounding meshes
        result = create_model_subset_from_xgen(instance)
        if not result:
            self.log.warning("No bound mesh been found.")
