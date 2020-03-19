"""
!!!Deprecating!!!
Maya script job for rendering Arnold standin by frame in Deadline

"""

import os
import json
import pyblish.api


if __name__ == "__main__":

    from maya import mel

    # Find extractor plugin
    plugin = None
    for p in pyblish.api.discover():
        if p.__name__ == "ExtractArnoldStandIn":
            plugin = p
            break

    assert plugin, "Pyblish plugin not found."

    # Parse data for extractor
    data_path = os.environ["REMOTE_DATA_PATH"]
    with open(data_path, "r") as fp:
        data = json.load(fp)

    # Frame range
    start = int(mel.eval("DeadlineValue(\"StartFrame\")"))
    end = int(mel.eval("DeadlineValue(\"EndFrame\")"))

    # Export
    plugin.export_ass(data, start, end, 1)
