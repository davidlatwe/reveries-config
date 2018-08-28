import pyblish.api

import maya.cmds as cmds


class CollectAnimationOutputs(pyblish.api.InstancePlugin):
    """Collect out hierarchy data for instance.
    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Animation Outputs"
    hosts = ["maya"]
    families = ["reveries.animation"]

    def process(self, instance):
        """Collect the hierarchy nodes"""

        family = instance.data["family"]
        out_set = next((member for member in instance if
                        member.endswith("OutSet")), None)

        assert out_set, ("Expecting OutSet for instance of family"
                         " '%s'" % family)

        members = cmds.ls(cmds.sets(out_set, query=True), long=True)

        # Store data in the instance for the validator
        instance.data["out_animation"] = members
