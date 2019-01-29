
import pyblish.api

from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidAction


class SelectInvalid(MayaSelectInvalidAction):

    label = "Select Bad Named"


class RepairInvalid(RepairInstanceAction):

    label = "Delete All Bad Named"


class ValidateAttributeNiceName(pyblish.api.InstancePlugin):
    """Validate user-defined attributes' human-readable name

    Ensure user-defined attributes' human-readable name (niceName) won't crash
    Maya.

    Maya's Attribute Spread Sheet GUI will crash if the length of 'niceName'
    >= 64 and contained any whitespace in the string, this should be Maya's
    bug. This bug has been confirmed exists in Maya 2016-18, before Autodesk
    Maya fix this, we need this validation.

    (NOTE) This bug was found while we exchanging model with FBX format, and
        the source of attribute name contained characters that will not be
        accepted by Maya, so those illegal characters get replaced with ascii
        code, further more, since those attributes only provided long name,
        Maya auto generate 'nice name' by seperating long name with uppercase
        and numeric characters then interpolated with whitespaces, therefore,
        super-long-nice-name created.

    (NOTE) This has been fixed in Maya 2018 update 3

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Attribute Nice Named"
    families = [
        "reveries.model",
        "reveries.rig",
        "reveries.look",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        if instance.context.data["mayaVersionAPI"] >= 20180300:
            return None

        invalid = dict()

        for node in instance:
            for attr in cmds.listAttr(node, userDefined=True) or list():
                nice = cmds.attributeQuery(attr, node=node, niceName=True)

                # niceName can't have any whitespace if longer then 64 chars
                if len(nice) >= 64 and " " in nice:
                    if node not in invalid:
                        invalid[node] = list()

                    invalid[node].append((attr, nice))

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            err_log = ""
            for node, attrs in invalid.items():
                err_log += node + "\n"
                for attr, nice in attrs:
                    err_log += "    {}\n".format(attr)
                    err_log += "    {}\n\n".format(nice)

            self.log.error(
                "'%s' has invalid attribute niceName:\n%s" % (
                    instance, err_log)
            )
            raise Exception("%s <Validate Attribute niceName> Failed."
                            % instance)

    @classmethod
    def fix(cls, instance):
        from maya import cmds

        invalid = cls.get_invalid(instance)

        for node, attrs in invalid.items():
            for attr_long, attr_nice in attrs:
                cmds.deleteAttr(node, attribute=attr_long)
