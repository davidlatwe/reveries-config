
import contextlib
import pyblish.api
import avalon.api


class ExtractRedshiftProxy(pyblish.api.InstancePlugin):
    """
    """
    # Will child texture instance be published when standin instance
    # is being delayed ?

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Redshift Proxy"
    families = [
        "reveries.rsproxy"
    ]

    def process(self, instance):
        from reveries import utils

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        repr_root = instance.data.get("reprRoot")

        start = int(instance.data["startFrame"])
        end = int(instance.data["endFrame"])
        step = int(instance.data["step"])
        has_yeti = instance.data.get("hasYeti", False)
        nodes = instance[:]

        use_sequence = start != end
        if use_sequence:
            pattern = "%s.%%04d.rs" % instance.data["subset"]
            firstfile = pattern % start
        else:
            pattern = "%s.rs" % instance.data["subset"]
            firstfile = pattern

        cachename = "%s.rs" % instance.data["subset"]
        outpath = "%s/%s" % (staging_dir, cachename)

        instance.data["outputPath"] = "%s/%s" % (staging_dir, pattern)

        use_sequence = start != end
        if use_sequence:
            instance.data["repr.RsProxy._hardlinks"] = [
                pattern % i for i in range(start, end + 1, step)]
        else:
            instance.data["repr.RsProxy._hardlinks"] = [firstfile]

        if repr_root:
            # Re-direct output path to custom root path
            staging_dir = staging_dir.replace(avalon.api.registered_root(),
                                              repr_root,
                                              1)
            instance.data["repr.RsProxy.reprRoot"] = repr_root

        instance.data["repr.RsProxy._stage"] = staging_dir
        instance.data["repr.RsProxy.entryFileName"] = firstfile
        instance.data["repr.RsProxy.useSequence"] = use_sequence

        self.log.info("Extracting proxy..")

        child_instances = instance.data.get("childInstances", [])
        try:
            texture = next(chd for chd in child_instances
                           if chd.data["family"] == "reveries.texture")
        except StopIteration:
            file_node_attrs = dict()
        else:
            file_node_attrs = texture.data.get("fileNodeAttrs", dict())

        instance.data["repr.RsProxy._delayRun"] = {
            "func": self.export_rs,
            "args": [
                nodes,
                outpath,
                file_node_attrs,
                has_yeti,
            ],
            "kwargs": {
                "start": start,
                "end": end,
                "step": step,
            }
        }

    def export_rs(self,
                  nodes,
                  outpath,
                  file_node_attrs,
                  has_yeti,
                  start,
                  end,
                  step):
        from maya import cmds, mel
        from reveries.maya import capsule

        render_settings = {
            # Ensure frame padding == 4
            # This might not needed in Redshift, the padding seems always
            # be 4, and won't affected by renderSettings.
            "defaultRenderGlobals.extensionPadding": 4,
        }

        # Yeti
        if has_yeti:
            # In Deadline, this is a script job instead of rendering job, so
            # the `pgYetiPreRender` Pre-Render MEL will not be triggered.
            # We need to call it by ourselve, or Yeti will complain about
            # cache temp dir not exist.
            mel.eval("pgYetiPreRender;")

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
            capsule.ref_edit_unlock(),
            # (NOTE) Ensure attribute unlock
            capsule.attribute_states(file_node_attrs.keys(), lock=False),
            # Change to published path
            capsule.attribute_values(file_node_attrs),
            # Fixed render settings
            capsule.attribute_values(render_settings),
        ):
            cmds.select(nodes, replace=True)
            files = cmds.rsProxy(filePath=outpath,
                                 selected=True,
                                 startFrame=start,
                                 endFrame=end,
                                 byFrame=step,
                                 connectivity=False,
                                 compress=True,
                                 # still export proxy when all objects are
                                 # not visible/renderable.
                                 allowEmpty=True)

            # If your texture folder used to be D:\Textures and now
            # it's E:\Textures, you can use the
            # `REDSHIFT_PATHOVERRIDE_FILE` or
            # `REDSHIFT_PATHOVERRIDE_STRING`
            # to tell Redshift to turn D:\Textures into E:\Textures.
            #
            # See redshift doc for environment variables.
