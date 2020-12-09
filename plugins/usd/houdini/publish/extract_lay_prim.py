import os

import pyblish.api


class ExtractLayoutPrim(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.22
    label = "Extract Layout USD Export"
    hosts = ["houdini"]
    families = [
        "reveries.layout.usd",
    ]

    def process(self, instance):
        from reveries import utils

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        filename = "lay_prim.usda"
        file_path = os.path.join(staging_dir, filename).replace('\\', '/')

        json_file_name = 'layout.json'
        json_file_path = os.path.join(staging_dir, json_file_name)

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [filename, json_file_name]
        instance.data["repr.USD.entryFileName"] = filename
        instance.data["subsetGroup"] = "Layout"
        # instance.data["step_type"] = "lay_prim"

        # TODO: Add frame range information
        # data["startFrame"] = int(node.evalParm("f1"))
        # data["endFrame"] = int(node.evalParm("f2"))

        self.shot_name = instance.data['asset']

        self._build(file_path)

        # Write json file
        self._write_json_file(usd_path=file_path, json_path=json_file_path)

        self._publish_instance(instance)

    def _build(self, file_path):
        from reveries.common.usd.pipeline import lay_prim_export
        lay_prim_export.build(file_path, self.shot_name)

    def _write_json_file(self, usd_path=None, json_path=None):
        from reveries.common.usd.pipeline import lay_json_export

        lay_json_export.export(usd_path, json_path, host="houdini")

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance
        publish_instance.run(instance)

        instance.data["_preflighted"] = True
