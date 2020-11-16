import pyblish.api


class ExtractPointCacheChildUSDExport(pyblish.api.InstancePlugin):
    """Publish pointcache child usd file.
    """

    order = pyblish.api.ExtractorOrder + 0.492
    hosts = ["maya"]
    label = "Extract PointCache (child usd)"
    families = [
        "reveries.pointcache.child.usd",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.maya.usd import pointcache_export
        from reveries.common import get_frame_range

        out_cache = instance.data.get("outCache")
        start_frame = instance.data.get("startFrame")
        end_frame = instance.data.get("endFrame")
        shot_name = instance.data['asset']

        if not out_cache:
            self.log.warning("No output geometry found in your scene.")
            return

        if not start_frame or not end_frame:
            start_frame, end_frame = get_frame_range(shot_name)

        staging_dir = utils.stage_dir()
        # === Export pointcache USD === #
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

        # Update information in instance data
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [
            file_info['authored_data'],  # authored_data.usda
            file_info['source'],  # source.usda
            file_info['main']  # pointcache_prim.usda
        ]
        instance.data["repr.USD.entryFileName"] = file_info['main']

        self._publish_instance(instance)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance
        publish_instance.run(instance)

        instance.data["_preflighted"] = True
