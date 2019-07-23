
import pyblish.api


class ExtractTxMapUpdate(pyblish.api.InstancePlugin):
    """Ensruing all .tx maps were update-to-date

    If already updated, it will skip. So should not taking too much time at
    this point.

    """

    order = pyblish.api.ExtractorOrder - 0.11  # Run before texture extractor
    label = "Ensure Tx Updated"
    hosts = ["maya"]
    families = [
        "reveries.texture"
    ]

    checked_flag = "__txUpdateChecked"

    def process(self, instance):
        if instance.context.data.get(self.checked_flag):
            self.log.debug("Tx maps update checked, skipping..")
            return

        if not instance.data.get("useTxMaps"):
            self.log.debug("No .tx map needed.")
            return

        self.update_tx()

        instance.context.data[self.checked_flag] = True

    def update_tx(self):
        from maya import cmds

        if cmds.pluginInfo("mtoa", query=True, loaded=True):
            import mtoa.core as core
        else:
            self.log.warning("Tx maps set to use, but Arnold did not loaded. "
                             "Unable to update and this might be a bug.")
            return

        self.log.info("Ensuring all .tx files updated..")
        # (NOTE) This was from the Arnold's utilities menu tool
        #        "Update TX Files". The command will not re-create .tx file
        #        if updated.
        core.createOptions()
        cmds.arnoldUpdateTx()
