import os
import json
import shutil
import traceback

import pyblish.api
from avalon import io, api


class ExtractLayoutPrim(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.22
    label = "Extract Layout USD Export"
    hosts = ["houdini"]
    families = [
        "reveries.layout",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common.usd import update_reference_path

        # auto_update = instance.data.get("autoUpdate", False)

        staging_dir = utils.stage_dir()
        filename = "lay_prim.usda"
        file_path = os.path.join(staging_dir, filename).replace('\\', '/')

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [filename]
        instance.data["repr.USD.entryFileName"] = filename
        instance.data["subsetGroup"] = "Layout"
        instance.data["step_type"] = "lay_prim"

        self.shot_name = instance.data['asset']

        self._build(file_path)

    def _build(self, file_path):
        from reveries.common.usd.pipeline import lay_prim_export
        lay_prim_export.build(file_path, self.shot_name)
