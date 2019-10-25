
from collections import defaultdict
from maya import cmds

import pyblish.api

from avalon.maya.pipeline import AVALON_CONTAINER_ID

from reveries.maya import lib, pipeline
from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidInstanceAction
from reveries.maya import utils


class SelectMissing(MayaSelectInvalidInstanceAction):

    label = "沒有編號"
    symptom = "missing"


class SelectDuplicated(MayaSelectInvalidInstanceAction):

    label = "重複編號"
    symptom = "duplicated"


class SelectMissMatchedAsset(MayaSelectInvalidInstanceAction):

    label = "Asset Id 錯誤"
    symptom = "asset_id"


class RepairIDMissing(RepairInstanceAction):

    label = "沒有編號"
    symptom = "missing"


class RepairIDDuplicated(RepairInstanceAction):

    label = "重複編號"
    symptom = "duplicated"


class RepairMissMatchedAsset(RepairInstanceAction):

    label = "Asset Id 錯誤"
    symptom = "asset_id"


def ls_subset_groups():
    groups = set()
    for node in lib.lsAttrs({"id": AVALON_CONTAINER_ID}):
        groups.add(pipeline.get_group_from_container(node))
    return groups


class ValidateAvalonUUID(pyblish.api.InstancePlugin):
    """物件要有編號 (AvalonID)

    Model mesh, XGen, rig 控制器, 攝影機, 燈光等等物件需要被打上正確的
    編碼。這是為了之後套材質 (look) 或者套動態 (animCurve) 時的資料配對。

    AvalonID 通常看起來像這樣:

        5da7d9fa2ec7db73c0d2fe77:5dadbe36ed9f0d8638c021eb
        |------ Asset Id ------| |----- Object Id ------|

    是由兩串編碼加上中間區隔的冒號組成，這個資料會寫在物件的 ".AvalonID"
    屬性。

    這個驗證的錯誤狀況有三種:
        1. 沒有編號
        2. 重複編號
        3. Asset Id 錯誤

    請根據錯誤訊息來執行相對應的修正動作。

    """

    order = pyblish.api.ValidatorOrder - 0.12
    hosts = ["maya"]
    label = "物件編號指派正確"

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
        pyblish.api.Category("選取"),
        SelectMissing,
        SelectDuplicated,
        SelectMissMatchedAsset,
        pyblish.api.Category("修正"),
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
            nodes = set()
            for member in uuids.values():
                nodes.update(member)

            ids = set()
            for node in nodes:
                id = utils.get_id(node)
                if id is None:
                    continue
                if id not in ids:
                    ids.add(id)
                else:
                    invalid.append(node)

        return invalid

    @classmethod
    def get_invalid_asset_id(cls, instance, uuids=None):

        if instance.data["family"] in cls.loose_uuid:
            return

        if instance.data["family"] == "reveries.rig":
            # Rig's model may coming from multiple assets
            return

        if uuids is None:
            uuids = cls._get_avalon_uuid(instance)

        invalid = uuids.get("missMatched", [])

        return invalid

    def echo(self, instance, invalid, cause):
        self.log.error(
            "'{}' {} :\n{}".format(
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
            self.echo(instance, invalid, "發現部分物件**沒有**編號")

        invalid = self.get_invalid_duplicated(instance, uuids_dict)
        if invalid:
            IS_INVALID = True
            self.echo(instance, invalid, "發現**重複**編號的物件")

        invalid = self.get_invalid_asset_id(instance, uuids_dict)
        if invalid:
            IS_INVALID = True
            self.echo(instance, invalid, "發現 Asset Id 錯誤")

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
                    # Wipe out invalid Id's verifier so to force Id renew
                    varifier = node + "." + utils.Identifier.ATTR_VERIFIER
                    cmds.setAttr(varifier, "", type="string")
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

            if cmds.referenceQuery(node, isNodeReferenced=True):
                continue

            state = utils.get_id_status(node)
            id_ns = utils.get_id_namespace(node)
            if not id_ns:
                # Must have id namespace
                state = utils.Identifier.Untracked

            uuids[state].append(node)

            if id_ns and not id_ns == asset_id:
                uuids["missMatched"].append(node)

        return uuids
