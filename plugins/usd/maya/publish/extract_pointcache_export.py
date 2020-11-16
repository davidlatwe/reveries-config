import os

import pyblish.api


class ExtractPointCacheUSDExport(pyblish.api.InstancePlugin):
    """Publish parent pointcache usd file.
    """

    order = pyblish.api.ExtractorOrder + 0.4921
    hosts = ["maya"]
    label = "Extract PointCache (main usd)"
    families = [
        "reveries.pointcache.usd",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.maya.usd import pointcache_export
        from reveries.common import get_frame_range

        if instance.data.get("isDummy"):
            return

        out_cache = instance.data.get("outCache")
        start_frame = instance.data.get("startFrame")
        end_frame = instance.data.get("endFrame")
        self.subset_name = instance.data["subset"]
        self.shot_name = instance.data["asset"]

        if not out_cache:
            self.log.warning("No output geometry found in your scene.")
            return

        if not start_frame or not end_frame:
            start_frame, end_frame = get_frame_range(self.shot_name)
        self.frame_range = [start_frame, end_frame]

        staging_dir = utils.stage_dir()

        # === Export Pointcache USD === #
        exporter = pointcache_export.PointCacheExporter(
            output_dir=staging_dir,
            export_node=instance.data.get("export_node"),
            root_usd_path=instance.data.get("root_usd_path"),
            frame_range=[start_frame, end_frame],
            asset_name=instance.data.get("asset_name"),
            out_cache=out_cache
        )
        exporter.export_usd()

        file_info = exporter.files_info

        # === Generate parent USD === #
        self.parent_usd_file = "parent_pointcache_prim.usda"
        parent_result = self._generate_parent_usd(staging_dir, file_info)

        # Update information in instance data
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [
            file_info['authored_data'],  # authored_data.usda
            file_info['source'],  # source.usda
            file_info['main']  # pointcache_prim.usda
        ]
        instance.data["repr.USD.entryFileName"] = file_info['main']

        if parent_result:
            instance.data["repr.USD._files"].append(self.parent_usd_file)

        self._publish_instance(instance)

    def _generate_parent_usd(self, staging_dir, file_info):
        from reveries.maya.usd import parent_pointcache_export

        # Export main usd file
        exporter = parent_pointcache_export.ParentPointcacheExporter(
            self.shot_name,
            self.subset_name,  # parent subset name
            frame_range=self.frame_range
        )

        if exporter.get_children_data():
            exporter.export(staging_dir)
            final_main_usd_path = exporter.output_path

            if os.path.exists(final_main_usd_path):
                # === Generate main usd === #
                main_usd_path = os.path.join(
                    staging_dir, file_info['main']).replace('\\', '/')
                pre_main_path = os.path.join(
                    staging_dir, self.parent_usd_file).replace('\\', '/')

                # Rename pre_main usd file
                os.rename(main_usd_path, pre_main_path)

                # Rename main usd file
                os.rename(final_main_usd_path, main_usd_path)

                return True

        return False

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance
        publish_instance.run(instance)

        instance.data["_preflighted"] = True
