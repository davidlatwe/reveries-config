from avalon import api


class CreateWrite(api.Creator):
    """Setup Write node for submitting to Deadline

    Create new write node or use selected write node and imprint
    data into it.

    """

    label = "Write"
    family = "reveries.write"
    icon = "film"
    hosts = ["nuke"]

    def process(self):
        from collections import OrderedDict
        from avalon.nuke import lib
        from reveries import lib as reveries_lib
        import nuke

        with lib.maintained_selection():
            if not (self.options or {}).get("useSelection"):
                lib.reset_selection()

            existed_write = next(
                (n for n in nuke.selectedNodes() if n.Class() == "Write"),
                None
            )
            instance = existed_write or nuke.createNode("Write")

            data = OrderedDict([
                (("divid", ""), lib.Knobby("Text_Knob", "")),
                ("deadlineSuspendJob", False),
                ("deadlinePriority", 80),
                ("deadlinePool", reveries_lib.get_deadline_pools()),
            ])
            self.data.update(data)

            lib.imprint(instance, self.data, tab="avalon")

        return instance
