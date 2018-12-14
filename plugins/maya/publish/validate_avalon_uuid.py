
from collections import defaultdict
from maya import cmds

import pyblish.api

from avalon.maya.pipeline import AVALON_CONTAINER_ID

from reveries.maya import lib, pipeline
from reveries.maya.utils import Identifier, get_id_status, set_avalon_uuid
from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidAction


class SelectMissing(MayaSelectInvalidAction):

    label = "Select ID Missing"
    symptom = "missing"


class SelectDuplicated(MayaSelectInvalidAction):

    label = "Select ID Duplicated"
    symptom = "duplicated"


class RepairInvalid(RepairInstanceAction):

    label = "Regenerate AvalonUUID"


def ls_subset_groups():
    groups = set()
    for node in lib.lsAttrs({"id": AVALON_CONTAINER_ID}):
        groups.add(pipeline.get_group_from_container(node))
    return groups


def get_avalon_uuid(instance):
    """
    Recoed every mesh's transform node's avalon uuid attribute
    """
    uuids = defaultdict(list)
    group_nodes = ls_subset_groups()

    for node in instance:
        if not cmds.nodeType(node) == "transform":
            continue

        if node in group_nodes:
            # Subset groups are auto generated on reference, meaningless
            # to have id.
            continue

        # get uuid
        uuids[get_id_status(node)].append(node)

    return uuids


class ValidateAvalonUUID(pyblish.api.InstancePlugin):
    """All transfrom must have an UUID
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Avalon UUID"
    actions = [
        pyblish.api.Category("Select"),
        SelectMissing,
        SelectDuplicated,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    @classmethod
    def get_invalid_missing(cls, instance, uuids=None):

        if uuids is None:
            uuids = get_avalon_uuid(instance)

        invalid = uuids.get(Identifier.Untracked, [])

        return invalid

    @classmethod
    def get_invalid_duplicated(cls, instance, uuids=None):

        if uuids is None:
            uuids = get_avalon_uuid(instance)

        invalid = [node for node in uuids.get(Identifier.Duplicated, [])
                   if ":" not in node]

        return invalid

    def process(self, instance):

        uuids_dict = get_avalon_uuid(instance)

        is_invalid = False

        invalid = self.get_invalid_missing(instance, uuids_dict)
        if invalid:
            is_invalid = True
            self.log.error(
                "'%s' Missing ID attribute on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )

        invalid = self.get_invalid_duplicated(instance, uuids_dict)
        if invalid:
            is_invalid = True
            self.log.error(
                "'%s' Duplicated IDs on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )

        if is_invalid:
            raise Exception("%s <Avalon UUID> Failed." % instance)

    @classmethod
    def fix(cls, instance):
        invalid = (cls.get_invalid_missing(instance) +
                   cls.get_invalid_duplicated(instance))
        for node in invalid:
            set_avalon_uuid(node)
