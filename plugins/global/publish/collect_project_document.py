
import pyblish.api
import avalon.api
import avalon.io


class CollectProjectDocument(pyblish.api.ContextPlugin):
    """Collect project document from database

    keys in context.data:
        * projectDoc

    """

    label = "Find Project Document"
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):

        project = avalon.io.find_one({"type": "project"})
        assert project is not None, "Could not find project document."

        context.data["projectDoc"] = project
