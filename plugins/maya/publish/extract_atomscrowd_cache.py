
import os
import pyblish.api

from AtomsMaya.hostbridge.commands import MayaCommandsHostBridge
from AtomsMaya.hostbridge.atomsnode import MayaAtomsNodeHostBridge

from reveries.plugins import PackageExtractor


class ExtractAtomsCrowdCache(PackageExtractor):

    label = "Extract AtomsCrowd Cache"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.atomscrowd"]

    representations = [
        "atoms",
    ]

    def extract_atoms(self):
        start_frame = int(self.context.data.get("startFrame"))
        end_frame = int(self.context.data.get("endFrame"))

        package_path = self.create_package()

        entry_file = self.file_name("atoms")
        entry_path = os.path.join(package_path, entry_file)

        cache_dir = str(os.path.dirname(entry_path))
        cache_name = str(os.path.basename(entry_path).replace(".atoms", ""))

        MayaCommandsHostBridge.export_atoms_cache(cache_dir,
                                                  cache_name,
                                                  start_frame,
                                                  end_frame,
                                                  self.data["AgentGroups"])

        variation_file = self.file_name("json")
        variation_path = os.path.join(package_path, variation_file)

        variation_str = MayaAtomsNodeHostBridge.get_variation_string()

        with open(variation_path, "w") as variation:
            variation.write(variation_str)

        self.add_data({
            "entryFileName": entry_file,
            "variationFile": variation_file,
        })
