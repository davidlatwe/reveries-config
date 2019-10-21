import pyblish.api
from avalon import api


class CollectTime(pyblish.api.ContextPlugin):
    """記下現在時間並紀錄為發佈時間"""

    label = "紀錄發佈時間"
    order = pyblish.api.CollectorOrder - 0.5

    def process(self, context):
        context.data["time"] = api.time()
