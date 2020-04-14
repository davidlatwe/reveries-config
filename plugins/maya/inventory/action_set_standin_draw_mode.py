
import avalon.api
import avalon.io


class SetStandInDrawMode(avalon.api.InventoryAction):

    label = "Stand-In Draw Mode"
    icon = "paint-brush"
    color = "#7BCD2E"

    @staticmethod
    def is_compatible(container):
        return container.get("loader") == "ArnoldAssLoader"

    def process(self, containers):
        from avalon.tools.sceneinventory import app
        from avalon.tools import widgets
        from avalon.vendor import qargparse
        from maya import cmds

        modes = [
            "Bounding Box",
            "Per Object Bounding Box",
            "Polywire",
            "Wireframe",
            "Point Cloud",
            "Shaded Polywire",
            "Shaded",
        ]

        options = [
            qargparse.Enum(name="drawMode",
                           label="Viewport Draw Mode",
                           items=modes,
                           default=0,
                           help="Arnold Stand-In viewport display mode.")
        ]

        dialog = widgets.OptionDialog(app.window)
        dialog.setWindowTitle("Set Stand-In Draw Mode")
        dialog.setMinimumWidth(300)
        dialog.create(options)

        if not dialog.exec_():
            return
        # Get option
        options = dialog.parse()
        mode = modes.index(options.get("drawMode", modes[0]))

        all_standins = list()
        for container in containers:
            if not container.get("loader") == "ArnoldAssLoader":
                continue

            member = cmds.sets(container["objectName"], query=True)
            standins = cmds.ls(member, type="aiStandIn")

            if not standins:
                continue

            all_standins += standins

        for standin in all_standins:
            cmds.setAttr(standin + ".mode", mode)
