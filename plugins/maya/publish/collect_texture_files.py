
import pyblish.api


class CollectTextureFiles(pyblish.api.InstancePlugin):
    """Collect texture data from each file nodes in instance

    Get file name pattern from file node and all files that exists in storage
    by the pattern string with color space setting.

    """

    order = pyblish.api.CollectorOrder + 0.4
    label = "Texture File Path"
    hosts = ["maya"]
    families = [
        "reveries.texture",
    ]

    def process(self, instance):
        import os
        from maya import cmds
        from maya.app.general.fileTexturePathResolver import (
            getFilePatternString,
            findAllFilesForPattern,
        )

        file_data = list()

        for file_node in instance:

            color_space = cmds.getAttr(file_node + ".colorSpace")
            tiling_mode = cmds.getAttr(file_node + ".uvTilingMode")
            is_sequence = cmds.getAttr(file_node + ".useFrameExtension")
            file_path = cmds.getAttr(file_node + ".fileTextureName",
                                     expandEnvironmentVariables=True)

            file_path = file_path.replace("\\", "/")
            dir_name = os.path.dirname(file_path)

            pattern = getFilePatternString(file_path, is_sequence, tiling_mode)
            all_files = [
                os.path.basename(fpath) for fpath in
                findAllFilesForPattern(pattern, frameNumber=None)
            ]

            if not all_files:
                self.log.warning("%s file not exists." % file_node)
                continue

            fpattern = os.path.basename(pattern)

            if len(all_files) > 1:
                # If it's a sequence, include the dir name as the prefix
                # of the file pattern
                dir_name, seq_dir = os.path.split(dir_name)
                fpattern = seq_dir + "/" + fpattern
            else:
                seq_dir = None

            file_data.append({
                "node": file_node,
                "fpattern": fpattern,
                "colorSpace": color_space,
                "dir": dir_name,
                "seq": seq_dir,
                "fnames": all_files,
            })

        instance.data["fileData"] = file_data
