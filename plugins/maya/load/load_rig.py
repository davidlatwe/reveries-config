
import avalon.api
import avalon.maya

from reveries.maya.plugins import ReferenceLoader


class RigLoader(ReferenceLoader):
    """Specific loader for rigs

    This automatically creates an instance for animators upon load.

    """
    label = "Reference rig"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = ["reveries.rig"]

    representations = [
        "mayaBinary",
    ]

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds

        entry_path = self.file_path(data["entry_fname"])

        nodes = cmds.file(entry_path,
                          namespace=namespace,
                          reference=True,
                          returnNewNodes=True,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name))

        # Store for post-process
        self[:] = nodes
        if data.get("post_process", True):
            self._post_process(name, namespace, context, data)

    def _post_process(self, name, namespace, context, data):

        # TODO(marcus): We are hardcoding the name "OutSet" here.
        #   Better register this keyword, so that it can be used
        #   elsewhere, such as in the Integrator plug-in,
        #   without duplication.

        import maya.cmds as cmds

        output = next((node for node in self if
                       node.endswith("OutSet")), None)
        controls = next((node for node in self if
                         node.endswith("ControlSet")), None)

        assert output, "No OutSet in rig, this is a bug."
        assert controls, "No ControlSet in rig, this is a bug."

        # Find the roots amongst the loaded nodes
        roots = cmds.ls(self[:], assemblies=True, long=True)
        assert roots, "No root nodes in rig, this is a bug."

        asset = avalon.api.Session["AVALON_ASSET"]
        dependency = str(context["representation"]["_id"])

        # Create the animation instance
        with avalon.maya.maintained_selection():
            cmds.select([output, controls] + roots, noExpand=True)
            avalon.api.create(name=namespace,
                              asset=asset,
                              family="reveries.animation",
                              options={"useSelection": True},
                              data={"dependencies": dependency})
