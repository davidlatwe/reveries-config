
import pyblish.api

from reveries.maya.plugins import MayaSelectInvalidInstanceAction


def _hash(mesh):
    from reveries.maya import utils

    hasher = utils.MeshHasher()
    hasher.set_mesh(mesh)
    hasher.update_points()

    return hasher.digest()


def get_protected(instance):
    from avalon import io

    protected = dict()

    asset = instance.context.data["assetDoc"]
    subset = io.find_one({"type": "subset",
                          "parent": asset["_id"],
                          "name": instance.data["subset"]})

    if subset is not None:
        versions = io.find({"type": "version", "parent": subset["_id"]},
                           sort=[("name", -1)])

        for version in versions:
            repr = io.find_one({"type": "representation",
                                "parent": version["_id"],
                                "name": "mayaBinary"})

            lock_list = repr["data"].get("modelProtected")
            if lock_list is None:
                continue

            profile = repr["data"].get("modelProfile", dict())
            for id in lock_list:
                data = profile[id][0]  # Should have only one mesh per id
                name = data.pop("hierarchy")
                protected[name] = data

    return protected


class SelectChanged(MayaSelectInvalidInstanceAction):

    label = "Invalid Modified"
    symptom = "changed"


class ValidateModelProtectedUnchanged(pyblish.api.InstancePlugin):
    """Models that have been registered as protected should not be changed
    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder - 0.1
    hosts = ["maya"]
    label = "Protected Unchanged"
    actions = [
        pyblish.api.Category("Select"),
        SelectChanged,
    ]

    @classmethod
    def get_invalid_changed(cls, instance, protected=None):
        from maya import cmds

        invalid = list()

        protected = get_protected(instance)
        transforms = cmds.ls(instance, type="transform", long=True)
        for name, data in protected.items():
            if name not in transforms:
                continue

            mesh = cmds.listRelatives(name,
                                      shapes=True,
                                      path=True,
                                      noIntermediate=True,
                                      type="mesh")[0]

            if not data["points"] == _hash(mesh)["points"]:
                invalid.append(name)

        return invalid

    @classmethod
    def get_invalid_missing(cls, instance, protected=None):
        from maya import cmds

        invalid = list()

        protected = protected or get_protected(instance)
        transforms = cmds.ls(instance, type="transform", long=True)
        for name, data in protected.items():
            if name not in transforms:
                invalid.append(name)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid_missing(instance)
        if invalid:
            self.log.error("Protected model should not be renamed or removed.")
            self.log.warning("Following nodes are missing..")
            for node in invalid:
                self.log.warning(node)

        invalid = self.get_invalid_changed(instance)
        if invalid:
            self.log.error("Protected model should not be changed.")
            self.log.warning("Following nodes have been modified..")
            for node in invalid:
                self.log.warning(node)
