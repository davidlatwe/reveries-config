
import pyblish.api


class ValidateRenderLayerHasMember(pyblish.api.InstancePlugin):
    """RenderLayer must have member

    No empty renderLayer allowed. If using renderSetup, try switch
    to that renderLayer so the membership will be refreshed.
    (Possibly Maya renderSetup bug)

    """
    label = "RenderLayer Has Member"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = [
        "reveries.renderlayer",
    ]

    def process(self, instance):
        if not len(instance[:]):
            layer = instance.data["renderlayer"]
            self.log.critical("RenderLayer '%s' has no member." % layer)
            self.log.error("Try switch to that renderLayer to refresh "
                           "if it does have member.")
            raise Exception("RenderLayer possibly empty, see log..")

        # (NOTE) If using renderSetup, this might be a Maya bug
        #        (Found in Maya 2018.6), either listing connections
        #        of `.renderInfo` or using `editRenderLayerMembers`,
        #        both method returns no member.
