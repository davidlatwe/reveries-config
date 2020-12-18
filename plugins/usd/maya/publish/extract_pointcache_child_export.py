import pyblish.api
from avalon import io


class ExtractPointCacheChildUSDExport(pyblish.api.InstancePlugin):
    """Publish pointcache child usd file.
    """

    order = pyblish.api.ExtractorOrder + 0.4810
    hosts = ["maya"]
    label = "Extract PointCache (child usd)"
    families = [
        "reveries.pointcache.child.usd",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common import get_frame_range
        from reveries.common.build_delay_run import DelayRunBuilder

        out_cache = instance.data.get("outCache")
        start_frame = instance.data.get("startFrame")
        end_frame = instance.data.get("endFrame")

        file_info = {
            'authored_data': 'authored_data.usd',
            'source': 'source.usda',
            'main': 'pointcache_prim.usda'
        }
        instance.data['file_info'] = file_info

        if not out_cache:
            self.log.warning("No output geometry found in your scene.")
            return

        if not start_frame or not end_frame:
            shot_name = instance.data['asset']
            start_frame, end_frame = get_frame_range.get(shot_name)
            instance.data["startFrame"] = start_frame
            instance.data["endFrame"] = end_frame

        # Update information in instance data
        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [
            file_info['authored_data'],  # authored_data.usda
            file_info['source'],  # source.usda
            file_info['main']  # pointcache_prim.usda
        ]
        instance.data["repr.USD.entryFileName"] = file_info['main']
        instance.data["_preflighted"] = True

        # Create delay running
        delay_builder = DelayRunBuilder(instance)

        instance.data["repr.USD._delayRun"] = {
            "func": self._export_usd,
            "args": [
                delay_builder.instance_data, delay_builder.context_data
            ],
            # "order": 9
        }

    def _export_usd(self, instance_data, context_data):
        from reveries.maya.usd import pointcache_export

        # === Export pointcache USD === #
        exporter = pointcache_export.PointCacheExporter(
            output_dir=instance_data.get("repr.USD._stage"),
            export_node=instance_data.get("export_node"),
            root_usd_path=instance_data.get("root_usd_path"),
            frame_range=[
                instance_data.get("startFrame"), instance_data.get("endFrame")],
            asset_name=instance_data.get("asset_name"),
            out_cache=instance_data.get("outCache"),
            file_info=instance_data.get("file_info"),
            look_variant=instance_data.get("look_variant", "")
        )
        exporter.export_usd()

        self._check_subset_data_exists(instance_data)
        self._publish_instance(instance_data, context_data)

    def _check_subset_data_exists(self, instance_data):
        from reveries.common import str_to_objectid

        subset_name = instance_data["subset"]
        shot_id = str_to_objectid(instance_data["assetDoc"]["_id"])

        subset_filter = {
            'type': 'subset',
            'name': subset_name,
            'parent': shot_id
        }
        subset_data = [s for s in io.find(subset_filter)]

        if subset_data:
            subset_data = subset_data[0]
            _update = {}
            for _key in ["parent_pointcache_name", "subsetGroup"]:
                if not subset_data["data"].get(_key, ""):
                    _update.update(
                        {"data.{}".format(_key): instance_data[_key]}
                    )
            if _update:
                io.update_many(subset_filter, update={"$set": _update})

    def _publish_instance(self, instance_data, context_data):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance_data, context=context_data)
