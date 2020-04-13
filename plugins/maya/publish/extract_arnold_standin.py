
import contextlib
import pyblish.api
import avalon.api


class ExtractArnoldStandIn(pyblish.api.InstancePlugin):
    """
    """
    # Will child texture instance be published when standin instance
    # is being delayed ?

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Arnold Stand-In"
    families = [
        "reveries.standin"
    ]

    def process(self, instance):
        from reveries import utils

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])

        start = instance.data["startFrame"]
        end = instance.data["endFrame"]
        step = instance.data["step"]
        has_yeti = instance.data.get("hasYeti", False)
        nodes = instance[:]

        pattern = "%s.%%04d.ass" % instance.data["subset"]
        cachename = "%s.ass" % instance.data["subset"]

        firstfile = pattern % start
        outpath = "%s/%s" % (staging_dir, cachename)

        use_sequence = start != end
        if use_sequence:
            instance.data["repr.Ass._hardlinks"] = [
                pattern % i for i in range(start, end, step)]
        else:
            instance.data["repr.Ass._hardlinks"] = [firstfile]

        instance.data["repr.Ass._stage"] = staging_dir
        instance.data["repr.Ass.entryFileName"] = firstfile
        instance.data["repr.Ass.useSequence"] = use_sequence

        self.log.info("Extracting standin..")

        child_instances = instance.data.get("childInstances", [])
        try:
            texture = next(chd for chd in child_instances
                           if chd.data["family"] == "reveries.texture")
        except StopIteration:
            file_node_attrs = dict()
        else:
            file_node_attrs = texture.data.get("fileNodeAttrs", dict())

        instance.data["repr.Ass._delayRun"] = {
            "func": self.export_ass,
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

    def export_ass(self,
                   nodes,
                   outpath,
                   file_node_attrs,
                   has_yeti,
                   start,
                   end,
                   step):
        from maya import cmds, mel
        from reveries.maya import arnold, capsule

        # Ensure option created
        arnold.utils.create_options()

        arnold_tx_settings = {
            "defaultArnoldRenderOptions.autotx": False,
            "defaultArnoldRenderOptions.use_existing_tiled_textures": True,
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
            # Disable Auto TX update and enable to use existing TX
            capsule.attribute_values(arnold_tx_settings),
        ):
            cmds.select(nodes, replace=True)
            asses = cmds.arnoldExportAss(filename=outpath,
                                         selected=True,
                                         startFrame=start,
                                         endFrame=end,
                                         frameStep=step,
                                         expandProcedurals=True,
                                         boundingBox=True,
                                         # Mask:
                                         #      Shapes,
                                         #      Shaders,
                                         #      Override Nodes,
                                         #      Operators,
                                         #
                                         # mask=4152,  # No Color Manager
                                         mask=6200)  # With Color Manager

            # Change to environment var embedded path
            root = avalon.api.registered_root().replace("\\", "/")
            project = avalon.api.Session["AVALON_PROJECT"]

            for ass in asses:
                lines = list()
                has_change = False
                with open(ass, "r") as assf:
                    for line in assf.readlines():
                        if line.startswith(" filename "):
                            line = line.replace(root, "[AVALON_PROJECTS]", 1)
                            line = line.replace(project, "[AVALON_PROJECT]", 1)
                            has_change = True
                        lines.append(line)

                # Remove color manager
                # (NOTE): If Color Manager included,
                #         may raise error if rendering
                #         in Houdini or other DCC.
                try:
                    s = lines.index("color_manager_syncolor\n")
                except ValueError:
                    # No color manager found
                    pass
                else:
                    e = lines.index("}\n", s) + 1
                    lines = lines[:s] + lines[e:]
                    has_change = True

                # Re-write
                if has_change:
                    with open(ass, "w") as assf:
                        assf.write("".join(lines))
