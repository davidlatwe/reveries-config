
import pyblish.api
import maya.cmds as cmds


class CollectDeformedOutputs(pyblish.api.InstancePlugin):
    """Collect out geometry data for instance.
    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Deformed Outputs"
    hosts = ["maya"]
    families = [
        "reveries.pointcache",
    ]

    def process(self, instance):
        """Collect the hierarchy nodes"""

        out_set = next((member for member in instance if
                        member.endswith("OutSet")), None)

        if out_set:
            members = cmds.sets(out_set, query=True) or []
        else:
            members = instance[:]

        # Store data in the instance for the validator
        instance.data["outCache"] = cmds.ls(members,
                                            type="deformableShape",
                                            long=True)

        # Assign contractor
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.script"
