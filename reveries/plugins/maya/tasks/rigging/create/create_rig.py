from maya import cmds
import avalon.maya


class RigCreator(avalon.maya.Creator):
    """Animatable Controller"""

    name = "rigDefault"
    label = "Rig"
    family = "reveries.rig"
    icon = "sitemap"

    def process(self):
        instance = super(RigCreator, self).process()

        self.log.info("Creating Rig instance set up ...")

        controls = cmds.sets(name="controls_set", empty=True)
        pointcache = cmds.sets(name="out_set", empty=True)
        cmds.sets([controls, pointcache], forceElement=instance)
