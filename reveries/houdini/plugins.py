
import os

import avalon.io

from .pipeline import env_embedded_path
from .. import plugins

from ..utils import get_representation_path_


class HoudiniBaseLoader(plugins.PackageLoader):

    def file_path(self, representation):
        file_name = representation["data"]["entryFileName"]
        entry_path = os.path.join(self.package_path, file_name)

        if not os.path.isfile(entry_path):
            raise IOError("File Not Found: {!r}".format(entry_path))

        return env_embedded_path(entry_path)


class HoudiniUSDBaseLoader(HoudiniBaseLoader):

    def file_path(self, representation):
        import hou

        file_name = representation["data"]["entryFileName"]
        entry_path = os.path.join(
            self.package_path, file_name).replace("\\", "/")

        if not os.path.isfile(entry_path):
            hou.ui.displayMessage(
                "Error: File not exists - {}".format(entry_path),
                severity=hou.severityType.Warning
            )
            return False

        return env_embedded_path(entry_path)

    def update(self, container, representation):
        import hou
        from reveries.common.utils import project_root_path

        node = container["node"]

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        entry_path = self.file_path(representation)
        if not entry_path:
            return False

        entry_path = os.path.expandvars(entry_path)
        project_root_path = project_root_path(entry_path)

        version_is = representation["parent"]
        _filter = {"_id": version_is}
        version_data = avalon.io.find_one(_filter)
        version_name = "v{:03d}".format(int(version_data["name"]))

        # Get subset node
        subnet_path = node.parm("subnet_usd_path").eval()
        subnet_index = node.parm("usd_index").eval()
        subnet_node = hou.node(subnet_path)

        subnet_node.parm("ex_ver_name_{}".format(subnet_index)).set(
            version_name)
        subnet_node.parm("ex_file_path_{}".format(subnet_index)).set(
            project_root_path)

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})
