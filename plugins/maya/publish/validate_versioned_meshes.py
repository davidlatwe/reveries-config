
import pyblish.api
from avalon.pipeline import AVALON_CONTAINER_ID
from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidAction


class SelectInvalid(MayaSelectInvalidAction):

    label = "Select Invalid Meshes"


class DeleteUnversionedMeshes(RepairInstanceAction):

    label = "Delete Invalid Meshes"


class ValidateVersionedMeshes(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "All Meshes Has Versioned"
    families = [
        "reveries.imgseq.playblast",
        "reveries.imgseq.turntable",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
        pyblish.api.Category("Fix It"),
        DeleteUnversionedMeshes,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from reveries.maya import lib
        from maya import cmds

        containers = lib.lsAttr("id", AVALON_CONTAINER_ID)

        meshes = cmds.ls(type="mesh", noIntermediate=True, long=True)
        transforms = cmds.listRelatives(meshes, parent=True, fullPath=True)
        model_transforms = set(transforms)
        has_versioned = set()

        for model_transform in model_transforms:
            for set_ in cmds.listSets(object=model_transform) or []:
                if set_ in containers:
                    has_versioned.add(model_transform)

        return list(model_transforms - has_versioned)

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("Meshes not versioned.")

    @classmethod
    def fix(cls, instance):
        from maya import cmds
        for node in cls.get_invalid(instance):
            if cmds.objExists(node):
                nodes = cmds.listRelatives(node, allDescendents=True) or []
                nodes.append(node)
                # possibly locked
                cmds.lockNode(nodes, lock=False)
                cmds.delete(nodes)
