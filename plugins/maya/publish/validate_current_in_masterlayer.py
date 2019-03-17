
import pyblish.api
from maya import cmds


class ValidateCurrentInMasterLayer(pyblish.api.InstancePlugin):

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "In MasterLayer"
    families = [
        "reveries.imgseq.playblast"
    ]

    def process(self, instance):
        layer = cmds.editRenderLayerGlobals(query=True,
                                            currentRenderLayer=True)

        assert layer == "defaultRenderLayer", ("Should be in masterlayer.")
