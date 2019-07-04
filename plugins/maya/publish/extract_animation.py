
import os
import contextlib
import pyblish.api
from reveries.plugins import PackageExtractor
from reveries.maya import lib, capsule
from maya import cmds


class ExtractAnimation(PackageExtractor):
    """Extract animation curve
    """

    label = "Extract Animation"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = [
        "reveries.animation",
    ]

    representations = [
        "anim",
    ]

    def extract_anim(self):
        cmds.loadPlugin("animImportExport", quiet=True)

        package_path = self.create_package()

        entry_file = self.file_name("anim")
        entry_path = os.path.join(package_path, entry_file)

        sele_file = self.file_name("mel")
        sele_path = os.path.join(package_path, sele_file)

        # Save animated nodes with order
        with capsule.maintained_selection():
            cmds.select(self.data["outAnim"], replace=True)

            with contextlib.nested(
                capsule.namespaced(self.data["animatedNamespace"], new=False),
                capsule.relative_namespaced()
            ):
                # Save with basename
                with open(sele_path, "w") as fp:
                    fp.write("select -r\n" +
                             "\n".join(cmds.ls(sl=True)) +
                             ";")

        context_data = self.context.data
        start = context_data.get("startFrame")
        end = context_data.get("endFrame")

        with contextlib.nested(
            capsule.no_refresh(),
            capsule.maintained_selection(),
            capsule.undo_chunk(),
        ):
            lib.bake(self.data["outAnim"],
                     frame_range=(start, end),
                     shape=False)

            cmds.select(self.data["outAnim"], replace=True, noExpand=True)
            cmds.file(entry_path,
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
                               "controlPoints=1;"
                               "shapes=0;"

                               "copyKeyCmd="
                               "-animation objects "
                               "-option keys "
                               "-hierarchy none "
                               "-controlPoints 1 "
                               "-shape 0")
                      )

        self.add_data({"entryFileName": entry_file,
                       "animatedAssetId": self.data["animatedAssetId"]})
