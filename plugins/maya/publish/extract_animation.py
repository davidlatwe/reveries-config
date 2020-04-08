
import contextlib
import pyblish.api
from reveries import utils
from reveries.maya import lib, capsule
from maya import cmds


class ExtractAnimation(pyblish.api.InstancePlugin):
    """Extract animation curve
    """

    label = "Extract Animation"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = [
        "reveries.animation",
    ]

    def process(self, instance):
        cmds.loadPlugin("animImportExport", quiet=True)

        staging_dir = utils.stage_dir()
        script = "%s.mel" % instance.data["subset"]
        filename = "%s.anim" % instance.data["subset"]
        scriptpath = "%s/%s" % (staging_dir, script)
        outpath = "%s/%s" % (staging_dir, filename)

        animated_asset = instance.data["animatedAssetId"]

        instance.data["repr.anim._stage"] = staging_dir
        instance.data["repr.anim._files"] = [filename, script]
        instance.data["repr.anim.entryFileName"] = filename
        instance.data["repr.anim.animatedAssetId"] = animated_asset

        # Save animated nodes with order
        with capsule.maintained_selection():
            cmds.select(instance.data["outAnim"], replace=True)

            with contextlib.nested(
                capsule.namespaced(instance.data["animatedNamespace"],
                                   new=False),
                capsule.relative_namespaced()
            ):
                # Save with basename
                with open(scriptpath, "w") as fp:
                    fp.write("select -r\n" +
                             "\n".join(cmds.ls(sl=True)) +
                             ";")

        context_data = instance.context.data
        start = context_data["startFrame"]
        end = context_data["endFrame"]

        with contextlib.nested(
            capsule.no_refresh(),
            capsule.maintained_selection(),
            capsule.undo_chunk(),
        ):
            lib.bake(instance.data["outAnim"],
                     frame_range=(start, end),
                     shape=False)

            cmds.select(instance.data["outAnim"], replace=True, noExpand=True)
            cmds.file(outpath,
                      force=True,
                      typ="animExport",
                      exportSelectedAnim=True,
                      options=("options=keys;"
                               "hierarchy=none;"
                               "precision=17;"
                               "intValue=17;"
                               "nodeNames=1;"
                               "verboseUnits=0;"
                               "whichRange=1;"
                               "helpPictures=0;"
                               "useChannelBox=0;"
                               "controlPoints=0;"
                               "shapes=0;"

                               "copyKeyCmd="
                               "-animation objects "
                               "-option keys "
                               "-hierarchy none "
                               "-controlPoints 0 "
                               "-shape 0")
                      )
