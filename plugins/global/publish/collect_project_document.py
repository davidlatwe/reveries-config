
import pyblish.api
import avalon.api
import avalon.io


class CollectProjectDocument(pyblish.api.ContextPlugin):
    """從資料庫讀取 Project 文件"""

    """

    keys in context.data:
        * projectDoc

    """

    label = "取得 Project 文件"
    order = pyblish.api.CollectorOrder - 0.35

    def process(self, context):

        project = avalon.io.find_one({"type": "project"})
        assert project is not None, "Could not find project document."

        context.data["projectDoc"] = project
