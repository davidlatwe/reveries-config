
from collections import defaultdict
from maya import cmds

import pyblish.api

from avalon.maya.pipeline import AVALON_CONTAINER_ID

from reveries.maya import lib, pipeline
from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidInstanceAction
from reveries.maya import utils


class SelectMissing(MayaSelectInvalidInstanceAction):

    label = "ID Missing"
    symptom = "missing"


class SelectDuplicated(MayaSelectInvalidInstanceAction):

    label = "ID Duplicated"
    symptom = "duplicated"


class SelectMissMatchedAsset(MayaSelectInvalidInstanceAction):

    label = "Invalid Asset ID"
    symptom = "asset_id"


class RepairIDMissing(RepairInstanceAction):

    label = "Fix Missing ID"
    symptom = "missing"


class RepairIDDuplicated(RepairInstanceAction):

    label = "Fix Duplicated ID"
    symptom = "duplicated"


class RepairMissMatchedAsset(RepairInstanceAction):

    label = "Fix Asset ID"
    symptom = "asset_id"


def ls_subset_groups():
    groups = set()
    for node in lib.lsAttrs({"id": AVALON_CONTAINER_ID}):
        groups.add(pipeline.get_group_from_container(node))
    return groups


class ValidateAvalonUUID(pyblish.api.InstancePlugin):
    """All transfrom and types required by each family must have an UUID

    To fix this, use *Fix It* action to regenerate UUIDs.

    """

    order = pyblish.api.ValidatorOrder - 0.12
    hosts = ["maya"]
    label = "Avalon UUID Assigned"

    strict_uuid = [
        "reveries.model",
        "reveries.rig",
        "reveries.look",
        "reveries.xgen",
        "reveries.camera",
        "reveries.lightset",
    ]

    loose_uuid = [
        "reveries.setdress",
        "reveries.mayashare",
    ]

    families = strict_uuid + loose_uuid

    actions = [
        pyblish.api.Category("Select"),
        SelectMissing,
        SelectDuplicated,
        SelectMissMatchedAsset,
        pyblish.api.Category("Fix It"),
        RepairIDMissing,
        RepairIDDuplicated,
        RepairMissMatchedAsset,
    ]

    @classmethod
    def get_invalid_missing(cls, instance, uuids=None):

        if uuids is None:
            uuids = cls._get_avalon_uuid(instance)

        invalid = uuids.get(utils.Identifier.Untracked, [])

        return invalid

    @classmethod
    def get_invalid_duplicated(cls, instance, uuids=None):

        if uuids is None:
            uuids = cls._get_avalon_uuid(instance)

        if instance.data["family"] in cls.loose_uuid:
            invalid = uuids.get(utils.Identifier.Duplicated, [])
        else:
            invalid = list()
            nodes = list()
            for member in uuids.values():
                nodes += member

            ids = set()
            for node in nodes:
                id = utils.get_id(node)
                if id not in ids:
                    ids.add(id)
                else:
                    invalid.append(node)
                    # Wipe out invalid Id's verifier so to force Id renew
                    varifier = node + "." + utils.Identifier.ATTR_VERIFIER
                    cmds.setAttr(varifier, "", type="string")

        return invalid

    @classmethod
    def get_invalid_asset_id(cls, instance, uuids=None):

        if instance.data["family"] in cls.loose_uuid:
            return

        if uuids is None:
            uuids = cls._get_avalon_uuid(instance)

        invalid = uuids.get("missMatched", [])

        return invalid

    def echo(self, instance, invalid, cause):
        self.log.error(
            "'%s' %s on:\n%s" % (
                instance,
                cause,
                ",\n".join("'" + member + "'" for member in invalid))
        )

    def process(self, instance):

        uuids_dict = self._get_avalon_uuid(instance)

        IS_INVALID = False

        invalid = self.get_invalid_missing(instance, uuids_dict)
        if invalid:
            IS_INVALID = True
            self.echo(instance, invalid, "Missing ID attribute")

        invalid = self.get_invalid_duplicated(instance, uuids_dict)
        if invalid:
            IS_INVALID = True
            self.echo(instance, invalid, "Duplicated IDs")

        invalid = self.get_invalid_asset_id(instance, uuids_dict)
        if invalid:
            IS_INVALID = True
            self.echo(instance, invalid, "Invalid Asset IDs")

        # End
        if IS_INVALID:
            raise Exception("%s <Avalon UUID> Failed." % instance)

    @classmethod
    def fix_invalid_missing(cls, instance):
        asset_id = str(instance.context.data["assetDoc"]["_id"])
        with utils.id_namespace(asset_id):
            for node in cls.get_invalid_missing(instance):
                if utils.get_id_status(node) == utils.Identifier.Clean:
                    utils.upsert_id(node, namespace_only=True)
                else:
                    utils.upsert_id(node)

    @classmethod
    def fix_invalid_duplicated(cls, instance):
        invalid = cls.get_invalid_duplicated(instance)

        if instance.data["family"] in cls.loose_uuid:
            # Do not renew id on these families
            utils.update_id_verifiers(invalid)
        else:
            # Re-assign unique id on duplicated
            asset_id = str(instance.context.data["assetDoc"]["_id"])
            with utils.id_namespace(asset_id):
                for node in invalid:
                    utils.upsert_id(node)

    @classmethod
    def fix_invalid_asset_id(cls, instance):

        if instance.data["family"] in cls.loose_uuid:
            return

        invalid = cls.get_invalid_asset_id(instance)

        asset_id = str(instance.context.data["assetDoc"]["_id"])
        with utils.id_namespace(asset_id):
            for node in invalid:
                utils.upsert_id(node, namespace_only=True)

    @classmethod
    def _get_avalon_uuid(cls, instance):
        uuids = defaultdict(list)
        group_nodes = ls_subset_groups()

        asset_id = str(instance.context.data["assetDoc"]["_id"])

        family = instance.data["family"]
        required_types = pipeline.uuid_required_node_types(family)

        nodes = cmds.ls(instance, long=True)  # Ensure existed nodes
        lock_state = cmds.lockNode(nodes, query=True, lock=True)
        for node, lock in zip(nodes, lock_state):
            if lock:
                cls.log.debug("Skipping locked node: %s" % node)
                continue

            if cmds.nodeType(node) not in required_types:
                continue

            if node in group_nodes:
                # Subset groups are auto generated on reference, meaningless
                # to have id.
                continue

            state = utils.get_id_status(node)
            id_ns = utils.get_id_namespace(node)
            if not id_ns:
                # Must have id namespace
                state = utils.Identifier.Untracked

            uuids[state].append(node)

            if not id_ns == asset_id:
                uuids["missMatched"].append(node)

        return uuids
