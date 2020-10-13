import os
import avalon
import traceback

import pyblish.api


class ValidatePathFromPublish(pyblish.api.InstancePlugin):
    """Validate all reference/sublayer path from publish."""

    order = pyblish.api.ValidatorOrder + 0.21

    label = "Validate Path From Publish"
    hosts = ["houdini"]
    families = [
        "reveries.env",
        "reveries.env.layer"
    ]

    def process(self, instance):
        import hou
        from reveries.common.usd import check_path_from_publish

        if instance.data.get("autoUpdate", False):
            return

        node = instance[0]

        try:
            node.render()
        except hou.Error as exc:
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))

        output_path = node.parm('lopoutput').eval()
        if not os.path.exists(output_path):
            raise ValueError("Output file not exists: {}".format(output_path))

        # Check process
        check_obj = check_path_from_publish.CheckPath.check(output_path)

        if check_obj.not_publish:
            lop_path = node.parm("loppath").eval()
            _paths = '<br>'.join(check_obj.not_publish)
            raise ValueError(
                "Below path not from publish, please double check your usd reference/sublayer: <br>"
                "{node_name} - {lop_path}: <br>"
                "{paths}".format(
                    node_name=node.name(),
                    lop_path=lop_path,
                    paths=_paths)
            )

