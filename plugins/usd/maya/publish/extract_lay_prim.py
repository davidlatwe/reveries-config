import os

import pyblish.api


class ExtractLayoutPrim(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.496
    label = "Extract Layout USD Export"
    hosts = ["maya"]
    families = [
        "reveries.layout.usd",
    ]

    def process(self, instance):
        from reveries import utils

        context_data = instance.context.data
        start = context_data["startFrame"]
        end = context_data["endFrame"]

        staging_dir = utils.stage_dir()
        filename = "lay_prim.usda"
        file_path = os.path.join(staging_dir, filename).replace('\\', '/')

        json_file_name = 'layout.json'
        json_file_path = os.path.join(staging_dir, json_file_name)

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [filename, json_file_name]
        instance.data["repr.USD.entryFileName"] = filename
        instance.data["subsetGroup"] = "Layout"
        # instance.data["step_type"] = "lay_prim"

        instance.data["startFrame"] = start
        instance.data["endFrame"] = end

        self.shot_name = instance.data['asset']

        self._build(file_path)

        # Write json file
        self._write_json_file(usd_path=file_path, json_path=json_file_path)

    def _build(self, file_path):
        from reveries.common.usd.pipeline import lay_prim_export
        lay_prim_export.build(file_path, self.shot_name)

    def _write_json_file(self, usd_path=None, json_path=None):
        from reveries.common.usd.pipeline import lay_json_export

        lay_json_export.export(usd_path, json_path, host="maya")
