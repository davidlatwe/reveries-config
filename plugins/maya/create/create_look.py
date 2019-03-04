
import avalon.maya

from reveries.maya.pipeline import put_instance_icon


class LookCreator(avalon.maya.Creator):
    """Shader connections defining shape look"""

    label = "Look"
    family = "reveries.look"
    icon = "paint-brush"

    defaults = [
        "default",
        "RigLow",
    ]

    def process(self):
        from maya import cmds

        renderlayer = cmds.editRenderLayerGlobals(query=True,
                                                  currentRenderLayer=True)
        self.data["renderlayer"] = renderlayer
        return put_instance_icon(super(LookCreator, self).process())
