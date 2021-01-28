import os
# import re
import pyblish.api


class _ValidateFileCacheAbs(pyblish.api.InstancePlugin):
    """Switch cache path to abs on "File Cache" node."""

    order = pyblish.api.ValidatorOrder + 0.22

    label = "Validate Cache Path is abs"
    hosts = ["houdini"]
    targets = ["deadline"]
    families = [
        "reveries.fx.layer_prim",
    ]

    def process(self, instance):
        import hou

        # "filecache" node: switch cache path to abs
        nodes = self._get_node(hou.node('/stage'), ["Sop/filecache"])
        self._switch_cache_path_to_abs(nodes)

        # "volume" node: switch hip to abs
        nodes = self._get_node(hou.node('/stage'), ["Lop/volume"])
        self._switch_volume_hip(nodes)

    def _get_node(self, node, _filter):
        # Return nodes of type matching the filter (i.e. geo etc...).
        result = []
        if node:
            for n in node.children():
                _type = n.type().nameWithCategory()
                if _type in _filter:
                    result.append(n)
                result += self._get_node(n, _filter)
        return result

    def _switch_cache_path_to_abs(self, nodes):
        _path_mapping = {
            0: os.environ.get("HIP", "None"),
            1: os.environ.get("JOB", "None"),
            2: os.environ.get("PRJ", "None"),
        }

        for node in nodes:
            _dir_parm = node.parm("select_set_dir")
            if _dir_parm:
                _value = _dir_parm.eval()
                if _value != 3:
                    _dir_parm.set("3")

                    if node.parm("optional_dir"):
                        node.parm("optional_dir").set(_path_mapping[_value])

    def _switch_volume_hip(self, nodes):
        for node in nodes:
            files_num = node.parm("files").eval()
            for _index in range(1, files_num+1):
                _parm = node.parm("filepath{}".format(_index))
                # _find = re.findall(
                #     "hou_parm.set\(\"(\\S+)\"\)", _parm.asCode())
                # source_path = _find[0] if _find else ""
                source_path = _parm.unexpandedString()
                if "$HIP" in source_path:
                    abs_path = source_path.replace("$HIP", os.environ["HIP"])
                    _parm.set(abs_path)
