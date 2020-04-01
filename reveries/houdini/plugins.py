
import os
from .pipeline import env_embedded_path
from .. import plugins, lib


class HoudiniBaseLoader(plugins.PackageLoader):

    def file_path(self, representation):
        file_name = representation["data"]["entryFileName"]
        entry_path = os.path.join(self.package_path, file_name)

        if not os.path.isfile(entry_path):
            raise IOError("File Not Found: {!r}".format(entry_path))

        return env_embedded_path(entry_path)


class HoudiniRenderExtractor(plugins.PackageExtractor):

    def render(self, ropnode):
        """
        Execute ROP node render if publish runs in localhost, or dump instance
        data for remote publish if the render is planned to run in Deadline.
        """
        import hou

        if not lib.to_remote():
            # Local rendering
            try:
                ropnode.render()
            except hou.Error as exc:
                # The hou.Error is not inherited from a Python Exception class,
                # so we explicitly capture the houdini error, otherwise pyblish
                # will remain hanging.
                import traceback
                traceback.print_exc()
                raise RuntimeError("Render failed: {0}".format(exc))

        else:
            packager = self.data["packager"]

            # Dump data for later publish in Python process
            pass

            # The output path will be swapped into published path
            # (per representation)
            packager.add_data({"swapRenderOutput": ropnode})


class HoudiniSelectInvalidInstanceAction(plugins.SelectInvalidInstanceAction):

    def select(self, invalid):
        self.deselect()
        for node in invalid:
            node.setSelected(True)

    def deselect(self):
        import hou
        hou.clearAllSelected()


class HoudiniSelectInvalidContextAction(plugins.SelectInvalidContextAction):
    """ Select invalid nodes in context"""

    def select(self, invalid):
        self.deselect()
        for node in invalid:
            node.setSelected(True)

    def deselect(self):
        import hou
        hou.clearAllSelected()
