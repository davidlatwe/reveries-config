
import avalon.api
import avalon.maya


class OpenMayaSource(object):

    label = "Open Work Scene"
    order = 99
    icon = "edit"
    color = "#666666"

    hosts = ["maya"]

    def __init__(self, context):
        pass

    def load(self, context, name, namespace, options):
        from maya import cmds

        if cmds.file(query=True, modified=True):

            _title = "Warning: Scene Not Saved"
            _message = "Save changes to untitled scene?"
            _save = "Save"
            _keep = "Don't Save"
            _stop = "Cancel"
            result = cmds.confirmDialog(title=_title,
                                        message=_message,
                                        button=[_save, _keep, _stop],
                                        defaultButton=_stop,
                                        cancelButton=_stop,
                                        dismissString=_stop)
            if result == _save:
                if avalon.maya.is_locked():
                    _message = "Scene is locked, please save under a new name."
                    cmds.confirmDialog(title="",
                                       message=_message,
                                       button=["OK"],
                                       defaultButton="OK",
                                       cancelButton="OK",
                                       dismissString="OK")
                    return

                # Save file if not locked
                cmds.SaveScene()
                if cmds.file(query=True, modified=True):
                    # Possible pressed the Cancel button in SaveAs Dialog
                    return

            elif result == _keep:
                pass

            elif result == _stop:
                return

        # Switch context before load
        avalon.api.update_current_task(task=context["version"]["data"]["task"],
                                       asset=context["asset"]["name"])
        cmds.file(modified=False)

        self.open_source_from_context(context)

    def open_source_from_context(self, context):
        from maya import cmds

        source = context["version"]["data"]["source"]
        file_path = source.format(root=avalon.api.registered_root())

        self.log.info("Opening file from: %s", file_path)

        cmds.file(file_path, o=True, prompt=True)


# Manually define which representation's source file can be accessed


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
