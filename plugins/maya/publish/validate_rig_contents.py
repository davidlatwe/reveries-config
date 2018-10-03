
import pyblish.api

from maya import cmds

from reveries.maya.plugins import MayaSelectInvalidAction


class SelectInvalidOutsiders(MayaSelectInvalidAction):

    label = "Select Outsiders"
    symptom = "outsider"


class SelectInvalidControls(MayaSelectInvalidAction):

    label = "Select Invalid Controls"
    symptom = "contorl_member"


class SelectInvalidOutNodes(MayaSelectInvalidAction):

    label = "Select Invalid Out Nodes"
    symptom = "out_member"


class ValidateRigContents(pyblish.api.InstancePlugin):
    """Ensure rig contains pipeline-critical content

    Every rig must contain at least two object sets:
        "ControlSet" - Set of all animatable controls
        "OutSet" - Set of all cachable meshes

    """

    label = "Rig Contents"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]

    families = ["reveries.rig"]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalidControls,
        SelectInvalidOutNodes,
        SelectInvalidOutsiders,
    ]

    @staticmethod
    def get_invalid_outsider(instance):
        invalid = list()

        all_members = cmds.sets("ControlSet", union="OutSet")

        for node in cmds.ls(all_members, long=True):
            if node not in instance:
                invalid.append(node)

        return invalid

    @staticmethod
    def get_invalid_contorl_member(instance):
        invalid = list()

        for node in cmds.sets("ControlSet", query=True):
            if not cmds.nodeType(node) == "transform":
                invalid.append(node)
                continue

            for chd in cmds.listRelatives(node, children=True) or []:
                if cmds.nodeType(node) == "mesh":
                    invalid.append(node)
                    break

        return invalid

    @staticmethod
    def get_invalid_out_member(instance):
        invalid = list()

        for node in cmds.sets("OutSet", query=True):
            if not cmds.nodeType(node) == "transform":
                invalid.append(node)
                continue

            if not cmds.listRelatives(node, children=True):
                invalid.append(node)
                continue

            for chd in cmds.listRelatives(node, children=True):
                if not cmds.nodeType(chd) == "mesh":
                    invalid.append(node)
                    break

        return invalid

    def process(self, instance):
        missing = list()

        for member in ("ControlSet",
                       "OutSet"):
            if member not in instance:
                missing.append(member)

        assert not missing, "\"%s\" has missing members: %s" % (
            instance, ", ".join("\"" + member + "\"" for member in missing))

        is_invalid = False

        invalid = self.get_invalid_outsider(instance)
        if invalid:
            is_invalid = True
            self.log.error(
                "'%s' does not have these members:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )

        invalid = self.get_invalid_contorl_member(instance)
        if invalid:
            is_invalid = True
            self.log.error(
                "'%s' has invalid controls:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )

        invalid = self.get_invalid_out_member(instance)
        if invalid:
            is_invalid = True
            self.log.error(
                "'%s' has invalid out nodes:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )

        if is_invalid:
            raise Exception("%s <Rig Contents> Failed." % instance)
