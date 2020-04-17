
import pyblish.api
from reveries import plugins


class SelectInvalidOutsiders(plugins.MayaSelectInvalidInstanceAction):

    label = "Select Outsiders"


class ValidateRigContents(pyblish.api.InstancePlugin):
    """Ensure rig contains pipeline-critical content

    Every rig must contain at least two object sets:
        "ControlSet" - Set of all animatable controls
        "OutSet" or "*OutSet" - Set of cachable meshes

    """

    label = "Rig Contents"
    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["maya"]

    families = ["reveries.rig"]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalidOutsiders,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        control_sets = instance.data["controlSets"]
        assert control_sets, "Must have 'ControlSet' in rig instance"

        out_sets = instance.data["outSets"]
        assert out_sets, "Must have at least one 'OutSet' in rig instance"

        # Ensure all controls are within the top group
        invalid = list()

        control_sets = instance.data["controlSets"]
        out_sets = instance.data["outSets"]

        all_members = cmds.sets(control_sets + out_sets, query=True)
        all_members = set(all_members or [])

        for node in cmds.ls(list(all_members), long=True):
            if node not in instance:
                invalid.append(node)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception(
                "'%s' does not have these nodes:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
