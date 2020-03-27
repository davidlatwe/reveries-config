
import json
import contextlib
import pyblish.api
from reveries import utils
from reveries.maya import xgen, capsule, utils as maya_utils


class ExtractXGenInteractive(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Interactive Groom"
    families = [
        "reveries.xgen.interactive",
    ]

    def process(self, instance):
        from maya import cmds

        staging_dir = utils.stage_dir()

        # Export preset
        # (NOTE) Saving as ext `.ma` instead of `.xgip` is because
        #        I'd like to use reference to load it later.
        #        Referencing file that was not `.ma`, `.mb` or other
        #        normal ext will crash Maya on file saving.
        filename = "%s.ma" % instance.data["subset"]
        linkfile = "%s.json" % instance.data["subset"]
        outpath = "%s/%s" % (staging_dir, filename)
        linkpath = "%s/%s" % (staging_dir, linkfile)

        instance.data["repr.XGenInteractive._stage"] = staging_dir
        instance.data["repr.XGenInteractive._files"] = [filename, linkfile]
        instance.data["repr.XGenInteractive.entryFileName"] = filename
        instance.data["repr.XGenInteractive.linkFname"] = linkfile

        bound_map = dict()
        clay_shader = "initialShadingGroup"
        descriptions = instance.data["igsDescriptions"]
        with capsule.assign_shader(descriptions, shadingEngine=clay_shader):

            for description in descriptions:

                desc_id = maya_utils.get_id(description)

                # Get bounded meshes
                bound_map[desc_id] = list()
                for mesh in xgen.interactive.list_bound_meshes(description):
                    transform = cmds.listRelatives(mesh, parent=True)
                    id = maya_utils.get_id(transform[0])
                    bound_map[desc_id].append(id)

            # (NOTE) Separating grooms and bounding meshes seems not able to
            #        preserve sculpt layer data entirely correct.
            #        For example, sculpting long hair strands to really short,
            #        may ends up noisy shaped after import back.
            #
            #        So now we export the grooms with bound meshes...
            #
            # io.export_xgen_IGS_presets(descriptions, outpath)

            with contextlib.nested(
                capsule.no_display_layers(instance[:]),
                capsule.maintained_selection(),
            ):
                cmds.select(descriptions)

                cmds.file(outpath,
                          force=True,
                          typ="mayaAscii",
                          exportSelected=True,
                          preserveReferences=False,
                          channels=True,
                          constraints=True,
                          expressions=True,
                          constructionHistory=True)

        # Parse preset bounding map

        with open(linkpath, "w") as fp:
            json.dump(bound_map, fp, ensure_ascii=False)
