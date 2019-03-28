
import os
import contextlib

import pyblish.api
from reveries.plugins import PackageExtractor
from reveries.maya import io, capsule

from maya import cmds


@contextlib.contextmanager
def unlock_colorspace(node):
    """
    """
    color_attr = node + ".colorSpace"
    color_space = cmds.getAttr(color_attr)
    cmds.setAttr(color_attr, lock=False)
    try:
        yield
    finally:
        cmds.setAttr(color_attr, color_space, lock=False, type="string")


@contextlib.contextmanager
def remove_file_env_path(data):
    """
    """
    root = data["relativeRoot"]
    replace = data["replaceRoot"]

    for node in data["fileNodes"]:
        # Must be starts with `root`, validated.
        origin_path = cmds.getAttr(node + ".fileTextureName")
        arnold_path = origin_path.replace(root, replace)

        with unlock_colorspace(node):
            cmds.setAttr(node + ".fileTextureName",
                         arnold_path,
                         type="string")
    try:
        yield
    finally:
        for node in data["fileNodes"]:
            arnold_path = cmds.getAttr(node + ".fileTextureName")
            origin_path = arnold_path.replace(replace, root)
            with unlock_colorspace(node):
                cmds.setAttr(node + ".fileTextureName",
                             origin_path,
                             type="string")


class ExtractArnoldStandIn(PackageExtractor):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Arnold Stand-In"
    families = [
        "reveries.standin"
    ]

    representations = [
        "Ass",
    ]

    def extract_Ass(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("ass")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
            capsule.ref_edit_unlock(),
            remove_file_env_path(self.data),
        ):
            cmds.select(self.member, replace=True)
            asses = cmds.arnoldExportAss(filename=cache_path,
                                         selected=True,
                                         startFrame=self.data["startFrame"],
                                         endFrame=self.data["endFrame"],
                                         frameStep=self.data["byFrameStep"],
                                         shadowLinks=1,
                                         lightLinks=1,
                                         mask=24)

        use_sequence = self.data["startFrame"] != self.data["endFrame"]
        cache_file = os.path.basename(asses[0])
        io.wrap_ass(entry_path,
                    [(cache_file, self.data["subset"])],
                    [use_sequence])

        self.add_data({"entryFileName": entry_file})
