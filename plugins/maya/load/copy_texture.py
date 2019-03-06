
import os
from distutils.dir_util import copy_tree

import avalon.api
from reveries.plugins import PackageLoader
from maya import cmds


class CopyTexturePack(PackageLoader, avalon.api.Loader):

    label = "Copy To Workspace"
    icon = "copy"
    color = "#D63948"

    hosts = ["maya"]

    families = ["reveries.texture"]

    representations = [
        "TexturePack",
    ]

    def load(self, context, name, namespace, options):

        _title = "Warning: Copying texture files"
        _message = ("This will copy textures to current workspace, may "
                    "take a while to complete.\n"
                    "Are you sure ?")
        _copy = "Copy"
        _stop = "Cancel"
        result = cmds.confirmDialog(title=_title,
                                    message=_message,
                                    button=[_copy, _stop],
                                    defaultButton=_stop,
                                    cancelButton=_stop,
                                    dismissString=_stop)

        if result == _copy:
            workspace = cmds.workspace(query=True, rootDirectory=True)
            entry = "textures"
            asset = context["asset"]["name"]
            subset = context["subset"]["name"]
            version = "v{:0>3}".format(context["version"]["name"])

            texture_dir = os.path.join(workspace,
                                       entry,
                                       asset,
                                       subset,
                                       version)

            cmds.waitCursor(state=True)
            try:
                copy_tree(self.package_path, texture_dir)
            except Exception:
                pass
            finally:
                cmds.waitCursor(state=False)
