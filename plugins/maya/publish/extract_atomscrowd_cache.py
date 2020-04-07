
import os
import pyblish.api

from reveries.plugins import PackageExtractor


class ExtractAtomsCrowdCache(PackageExtractor):

    label = "Extract AtomsCrowd Cache"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.atomscrowd"]

    representations = [
        "atoms",
    ]

    def extract_atoms(self, packager):
        from AtomsMaya.hostbridge.commands import MayaCommandsHostBridge

        packager.skip_stage()

        if self.data.get("useCustomRange"):
            start_frame = int(self.data["startFrame"])
            end_frame = int(self.data["endFrame"])
        else:
            start_frame = int(self.context.data.get("startFrame"))
            end_frame = int(self.context.data.get("endFrame"))

        package_path = packager.create_package()

        entry_file = packager.file_name("atoms")
        entry_path = os.path.join(package_path, entry_file)

        cache_dir = str(os.path.dirname(entry_path))
        cache_name = str(os.path.basename(entry_path).replace(".atoms", ""))

        agent_groups = self.data["AtomsAgentGroups"]
        MayaCommandsHostBridge.export_atoms_cache(cache_dir,
                                                  cache_name,
                                                  start_frame,
                                                  end_frame,
                                                  agent_groups)

        variation_file = packager.file_name("json")
        variation_path = os.path.join(package_path, variation_file)

        with open(variation_path, "w") as variation:
            variation.write(self.data["variationStr"])

        packager.add_data({
            "entryFileName": entry_file,
            "variationFile": variation_file,
            "startFrame": start_frame,
            "endFrame": end_frame,
        })
