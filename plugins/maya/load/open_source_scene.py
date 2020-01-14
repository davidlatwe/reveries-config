
import avalon.api
import avalon.maya


class OpenMayaSource(object):

    label = "Open Work Scene"
    order = 99
    icon = "edit"
    color = "#666666"

    hosts = ["maya"]

    is_utility = True

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
                    self.log.error("Modification unsaved, abort opening "
                                   "work scene.")
                    return

            elif result == _keep:
                pass

            elif result == _stop:
                return

        cmds.file(modified=False)

        self.open_source_from_context(context)

    def open_source_from_context(self, context):
        from maya import cmds

        version_data = context["version"]["data"]

        source = version_data["source"]
        file_path = source.format(root=avalon.api.registered_root())

        # Switch context before load
        current_user = avalon.api.Session.get("AVALON_USER", "")

        author = version_data["author"]
        avalon.api.Session["AVALON_USER"] = author
        avalon.api.update_current_task(task=version_data["task"],
                                       asset=context["asset"]["name"])

        work_dir = version_data.get("workDir")
        if work_dir:
            work_dir = work_dir.format(root=avalon.api.registered_root())
            avalon.api.Session["AVALON_WORKDIR"] = work_dir
            avalon.maya.pipeline._set_project()

        self.log.info("Opening file from: %s", file_path)

        cmds.file(file_path, o=True, force=True)

        if current_user:
            avalon.api.Session["AVALON_USER"] = current_user
        else:
            avalon.api.Session.pop("AVALON_USER")


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


class OpenSourcePointCache(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.pointcache"]
    representations = ["Alembic", "FBXCache", "GPUCache"]


class OpenSourceCamera(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.camera"]
    representations = ["mayaAscii"]


class OpenSourceSetDress(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.setdress"]
    representations = ["setPackage"]


class OpenSourceXGen(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.xgen"]
    representations = ["XGenLegacy", "XGenInteractive"]


class OpenSourceAiStandIn(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.standin"]
    representations = ["Ass"]


class OpenSourceAtomsCrowdCache(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.atomscrowd"]
    representations = ["atoms"]


class OpenSourceShared(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.mayashare"]
    representations = ["mayaAscii"]


class OpenSourceImgseq(OpenMayaSource, avalon.api.Loader):
    """Deprecated"""
    families = ["reveries.imgseq"]
    representations = ["imageSequence", "imageSequenceSet"]


class OpenSourceRenderlayer(OpenMayaSource, avalon.api.Loader):

    families = ["reveries.renderlayer"]
    representations = ["renderLayer"]
