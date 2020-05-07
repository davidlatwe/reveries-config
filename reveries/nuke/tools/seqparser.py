
import nuke
from collections import OrderedDict
from avalon.nuke import lib, command
from reveries.nuke import lib as nuke_lib


SEQUENCE_KEYS = ["name", "resolution"]


def build_layers(sequences):
    if not sequences:
        return

    lib.reset_selection()

    with command.viewer_update_and_undo_stop():
        group = nuke.createNode("Group")

        with nuke_lib.group_scope(group):

            aovs = OrderedDict()
            has_beauty = any("beauty" == i["name"] for i in sequences)

            for item in sorted(sequences, key=lambda i: i["name"].lower()):
                aov_name = item["name"]
                item["_resolved"] = item["root"] + "/" + item["fpattern"]

                read = nuke.Node("Read")
                read["selected"].setValue(False)
                read.autoplace()
                aovs[aov_name] = read

                _set_path(read, aov_name=aov_name, path=item["_resolved"])
                _set_format(read, item["resolution"])
                _set_range(read, start=item["start"], end=item["end"])

                # Mark aov name
                lib.set_avalon_knob_data(read, {("aov", "AOV"): aov_name})

            beauty = aovs.pop("beauty") if has_beauty else aovs.popitem()[1]
            nuke_lib.exr_merge(beauty, aovs.values())

            output = nuke.createNode("Output")
            output.autoplace()

        stamp = nuke.createNode("PostageStamp")
        stamp.setName("parsedLayers")
        group.setName("master")

    for item in sequences:
        pass


def _set_path(read, aov_name, path):
    read["file"].setValue(path)
    read["label"].setValue(aov_name)


def _set_range(read, start, end):
    start, end = int(start), int(end)
    read["first"].setValue(start)
    read["last"].setValue(end)
    read["origfirst"].setValue(start)
    read["origlast"].setValue(end)


def _set_format(read, resolution):
    w, h = resolution
    for format in nuke.formats():
        if format.width() == w and format.height() == h:
            try:
                read["format"].setValue(format.name())
            except TypeError:
                nuke.warning("Unrecognized format")
            finally:
                break
