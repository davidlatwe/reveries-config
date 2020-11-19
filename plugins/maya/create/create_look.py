
import avalon.maya

from reveries.maya.pipeline import put_instance_icon


class LookCreator(avalon.maya.Creator):
    """發佈材質 (包含貼圖, 模型渲染相關參數)"""

    label = "Look"
    family = "reveries.look"
    icon = "paint-brush"

    defaults = [
        "default",
        "RigHigh",
        "RigLow",
    ]

    def process(self):
        from maya import cmds

        renderlayer = cmds.editRenderLayerGlobals(query=True,
                                                  currentRenderLayer=True)
        self.data["renderlayer"] = renderlayer
        self.data["byNodeName"] = False
        return put_instance_icon(super(LookCreator, self).process())
