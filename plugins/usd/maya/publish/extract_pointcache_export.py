import os

import pyblish.api


class ExtractPointCacheUSDExport(pyblish.api.InstancePlugin):
    """Publish parent pointcache usd file.
    """

    order = pyblish.api.ExtractorOrder + 0.4811
    hosts = ["maya"]
    label = "Extract PointCache (main usd)"
    families = [
        "reveries.pointcache.usd",
    ]

    def process(self, instance):
        from reveries import utils

        from reveries.common import get_frame_range
        from reveries.common.build_delay_run import DelayRunBuilder

        if instance.data.get("isDummy"):
            return

        out_cache = instance.data.get("outCache")
        start_frame = instance.data.get("startFrame")
        end_frame = instance.data.get("endFrame")

        if not out_cache:
            self.log.warning("No output geometry found in your scene.")
            return

        if not start_frame or not end_frame:
            shot_name = instance.data["asset"]
            start_frame, end_frame = get_frame_range.get(shot_name)
            instance.data["startFrame"] = start_frame
            instance.data["endFrame"] = end_frame

        self.frame_range = [start_frame, end_frame]

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        file_info = {
            'authored_data': 'authored_data.usda',
            'source': 'source.usda',
            'main': 'pointcache_prim.usda'
        }
        instance.data['file_info'] = file_info

        # Update information in instance data
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
            "order": 10
        }
        instance.data["deadline_dependency"] = self.get_child_instance(instance)

    def get_child_instance(self, instance):
        context = instance.context
        child_instances = []

        for _instance in context:
            if _instance.data["family"] == "reveries.pointcache.child.usd":
                if str(_instance.data.get("parent_pointcache_name", "")) == \
                        str(instance.data["subset"]):
                    child_instances.append(_instance)

        return child_instances

    def _export_usd(self, instance_data, context_data):
        from reveries.maya.usd import pointcache_export

        staging_dir = instance_data.get("repr.USD._stage")
        file_info = instance_data.get("file_info")

        # === Export Pointcache USD === #
        exporter = pointcache_export.PointCacheExporter(
            output_dir=staging_dir,
            export_node=instance_data.get("export_node"),
            root_usd_path=instance_data.get("root_usd_path"),
            frame_range=[
                instance_data.get("startFrame"), instance_data.get("endFrame")],
            asset_name=instance_data.get("asset_name"),
            out_cache=instance_data.get("outCache"),
            file_info=file_info
        )
        exporter.export_usd()

        # === Generate parent USD === #
        self.parent_usd_file = "parent_pointcache_prim.usda"
        parent_result = self._generate_parent_usd(instance_data, staging_dir, file_info)

        if parent_result:
            instance_data["repr.USD._files"].append(self.parent_usd_file)

        self._publish_instance(instance_data, context_data)

    def _generate_parent_usd(self, instance_data, staging_dir, file_info):
        from reveries.maya.usd import parent_pointcache_export

        shot_name = instance_data["asset"]
        subset_name = instance_data["subset"]

        # Export main usd file
        exporter = parent_pointcache_export.ParentPointcacheExporter(
            shot_name,
            subset_name,  # parent subset name
            frame_range=[
                instance_data.get("startFrame"), instance_data.get("endFrame")]
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

    def _publish_instance(self, instance_data, context_data):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance_data, context=context_data)
