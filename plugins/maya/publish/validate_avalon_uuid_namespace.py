
from maya import cmds

import pyblish.api

from reveries.maya import pipeline, utils
from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class RepairInvalid(RepairInstanceAction):

    label = "Update Namespace"


class ValidateAvalonUUIDNamespace(pyblish.api.InstancePlugin):
    """All transfrom and types required by each family must have a namespace
    prefixed Avalon UUID.

    The namespace is current Asset's ObjectId.

    To fix this, use *Fix It* action to update UUIDs.

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Avalon UUID Namespace"

    families = pipeline.UUID_REQUIRED_FAMILIES

    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidInstanceAction,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):

        invalid = list()

        asset_id = str(instance.context.data["assetDoc"]["_id"])

        family = instance.data["family"]
        required_types = pipeline.uuid_required_node_types(family)

        lock_state = cmds.lockNode(instance, query=True, lock=True)
        for node, lock in zip(instance, lock_state):
            if lock:
                cls.log.debug("Skipping locked node: %s" % node)
                continue

            if cmds.nodeType(node) not in required_types:
                continue

            # get uuid namespace
            namespace = utils.get_id_namespace(node)
            if namespace != asset_id:
                invalid.append(node)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            pass

    @classmethod
    def fix_invalid(cls, instance):

        asset_id = str(instance.context.data["assetDoc"]["_id"])

        with utils.id_namespace(asset_id):
            for node in cls.get_invalid(instance):
                utils.upsert_id(node, namespace_only=True)
