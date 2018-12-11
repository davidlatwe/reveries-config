
import avalon.api


class OpenMayaSource(object):

    label = "Open Work Scene"
    order = 99
    icon = "edit"
    color = "#666666"

    hosts = ["maya"]

    def __init__(self, context):
        template = context["project"]["config"]["template"]["work"]

        data = {
            key: value["name"]
            for key, value in context.items()
        }

        data["root"] = avalon.api.registered_root()
        data["silo"] = context["asset"]["silo"]
        data["task"] = avalon.api.Session["AVALON_TASK"]
        data["app"] = avalon.api.Session["AVALON_APP"]

        fname = template.format(**data)
        self.fname = fname

    def load(self, context, name, namespace, options):
        self.open_source_from_context(context)

    def open_source_from_context(self, context):
        from maya import cmds

        source = context["version"]["data"]["source"]
        file_path = source.format(root=self.fname)

        cmds.file(file_path, o=True)


class OpenSourceModel(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.model"]
    representations = ["mayaBinary"]


class OpenSourceLook(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.look"]
    representations = ["LookDev"]


class OpenSourceRig(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.rig"]
    representations = ["mayaBinary"]


class OpenSourceAnimation(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.animation"]
    representations = ["mayaAscii"]


class OpenSourceCamera(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.camera"]
    representations = ["mayaAscii"]


class OpenSourceSetDress(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.setdress"]
    representations = ["setPackage"]
