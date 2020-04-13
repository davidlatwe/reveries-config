
import pyblish.api
from collections import defaultdict
from reveries import plugins


class SelectMissing(plugins.MayaSelectInvalidContextAction):

    label = "Renderlayer Missing"
    symptom = "missing"


class SelectNotUnique(plugins.MayaSelectInvalidContextAction):

    label = "Renderlayer Not Unique"
    symptom = "multiple"


class ValidateLookRenderlayers(pyblish.api.InstancePlugin):
    """Each lookDev subset should be paired with one unique renderlayer

    Each lookDev should be paried with one existing renderlayer and no
    renderlayer can be paired with multiple lookDev.

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Unique Renderlayers"
    families = ["reveries.look"]
    actions = [
        pyblish.api.Category("Select"),
        SelectMissing,
        SelectNotUnique,
    ]

    @classmethod
    def get_invalid_missing(cls, context):
        from maya import cmds

        missing = list()

        existed = cmds.ls(type="renderLayer")
        for instance in context:
            if not instance.data["family"] == "reveries.look":
                continue
            renderlayer = instance.data["renderlayer"]
            if renderlayer not in existed:
                missing.append(instance.data["objectName"])

        return missing

    @classmethod
    def get_invalid_multiple(cls, context):

        multiple = list()

        matched = defaultdict(list)
        for instance in context:
            if not instance.data["family"] == "reveries.look":
                continue
            renderlayer = instance.data["renderlayer"]
            matched[renderlayer].append(instance.data["objectName"])

        for layer, instances in matched.items():
            if len(instances) > 1:
                multiple += instances

        return multiple

    @plugins.context_process
    def process(self, context):
        is_invalid = False

        invalid = self.get_invalid_missing(context)
        if invalid:
            is_invalid = True
            self.log.error("Renderlayer missing:")
            for instance in invalid:
                self.log.error(instance)

        invalid = self.get_invalid_multiple(context)
        if invalid:
            is_invalid = True
            self.log.error("Renderlayer not unique:")
            for instance in invalid:
                self.log.error(instance)

        if is_invalid:
            raise Exception("LookDev not match with renderlayer correctly.")
