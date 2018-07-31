import pyblish.api


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

    def process(self, instance):
        missing = list()

        for member in ("ControlSet",
                       "OutSet"):
            if member not in instance:
                missing.append(member)

        assert not missing, "\"%s\" is missing members: %s" % (
            instance, ", ".join("\"" + member + "\"" for member in missing))
