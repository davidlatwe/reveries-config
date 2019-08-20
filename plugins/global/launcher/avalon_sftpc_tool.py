
from avalon import api, lib


class AvalonSFTPCAction(api.Action):
    """Avalon SFTPC
    """
    name = "avalon-sftpc"
    label = "Uploader"
    icon = "paper-plane"
    color = "#52D77B"
    order = 999     # at the end

    def is_compatible(self, session):
        return "AVALON_PROJECT" in session

    def process(self, session, **kwargs):
        return lib.launch(executable="python",
                          args=["-u", "-m", "avalon_sftpc"])
