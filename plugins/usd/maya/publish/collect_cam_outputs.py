
import pyblish.api
from avalon import io, api


class CollectCameraPrimUSDOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder - 0.09
    label = "Collect Camera Outputs"
    hosts = ["maya"]
    families = [
        "reveries.camera",
    ]

    def ins_exists(self, context, name):
        _exists = False
        for instance in context:
            if instance.data["subset"] == name:
                _exists = True
                break
        return _exists

    def subset_exists(self, subset_name):
        _filter = {
            "type": "subset",
            "name": subset_name,
            "parent": self.shot_id
        }
        subset_data = io.find_one(_filter)
        return subset_data

    def process(self, instance):
        self.shot_name = instance.data['asset']
        _filter = {"type": "asset", "name": self.shot_name}
        shot_data = io.find_one(_filter)
        self.shot_id = shot_data["_id"]

        # Create new instance
        context = instance.context
        backup = instance

        # Create camPrim
        name = 'camPrim'
        if not self.ins_exists(context, name):
            instance = context.create_instance(name)
            instance.data.update(backup.data)

            instance.data["family"] = "reveries.camera.usd"
            instance.data["subset"] = name

            self._check_version_pin(instance, name)

        # Create layPrim
        if api.Session["AVALON_TASK"].lower() in ["layout", "lay"]:
            name = 'layPrim'
            if not self.ins_exists(context, name) and \
                    not self.subset_exists(name):
                instance = context.create_instance(name)
                instance.data.update(backup.data)

                instance.data["family"] = "reveries.layout.usd"
                instance.data["subset"] = name
                self._check_version_pin(instance, name)

        # Create aniPrim
        if api.Session["AVALON_TASK"].lower() in \
                ["animation", "animating", "ani"]:
            name = 'aniPrim'
            if not self.ins_exists(context, name) and \
                    not self.subset_exists(name):
                instance = context.create_instance(name)
                instance.data.update(backup.data)

                instance.data["family"] = "reveries.ani.usd"
                instance.data["subset"] = name
                # self._check_version_pin(instance, name)

        name = 'finalPrim'
        if not self.ins_exists(context, name) and \
                not self.subset_exists(name):
            instance = context.create_instance(name)
            instance.data.update(backup.data)

            instance.data["family"] = "reveries.final.usd"
            instance.data["subset"] = name
            self._check_version_pin(instance, name)

    def _check_version_pin(self, instance, subset_name):
        shot_name = instance.data['asset']
        _filter = {"type": "asset", "name": shot_name}
        shot_data = io.find_one(_filter)

        # Get subset id
        _filter = {
            "type": "subset",
            "parent": shot_data['_id'],
            "name": subset_name  # "camPrim"/"layPrim"
        }
        subset_data = io.find_one(_filter)
        if subset_data:
            # Get version name
            _filter = {
                "type": "version",
                "parent": subset_data['_id'],
            }
            version_data = io.find_one(_filter, sort=[("name", -1)])
            if version_data:
                instance.data["versionPin"] = version_data["name"]
