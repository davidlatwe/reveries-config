
import os
from avalon.vendor import clique


def assemble(root, files, min_length=2):

    patterns = [
        clique.PATTERNS["frames"],
        clique.DIGITS_PATTERN,
    ]

    collections, remainder = clique.assemble(files,
                                             patterns=patterns,
                                             minimum_items=min_length)

    assert len(collections) > 0, "No sequence found in %s" % root
    assert len(collections) == 1, "More than one sequence found in %s" % root

    collection = collections[0]
    indexes = list(collection.indexes)

    head = collection.head
    padding = collection.padding
    tail = collection.tail
    start = indexes[0]
    end = indexes[-1]

    frame_str = "%%0%dd" % padding
    fpattern = "%s%s%s" % (head, frame_str, tail)

    return {
        "root": root.replace("\\", "/"),
        "head": head,
        "padding": padding,
        "paddingStr": frame_str,
        "tail": tail,
        "fpattern": fpattern,
        "start": start,
        "end": end,
    }


def ls_sequences(path, min_length=2):

    patterns = [
        clique.PATTERNS["frames"],
        clique.DIGITS_PATTERN,
    ]

    for root, dirs, files in os.walk(path):
        collections, remainder = clique.assemble(files,
                                                 patterns=patterns,
                                                 minimum_items=min_length)
        for collection in collections:
            indexes = list(collection.indexes)

            head = collection.head
            padding = collection.padding
            tail = collection.tail
            start = indexes[0]
            end = indexes[-1]

            relative = os.path.relpath(root, path).replace("\\", "/")
            relative = "" if relative == "." else (relative + "/")
            frame_str = "%%0%dd" % padding
            fpattern = "%s%s%s%s" % (relative, head, frame_str, tail)

            yield {
                "root": path.replace("\\", "/"),
                "head": head,
                "padding": padding,
                "paddingStr": frame_str,
                "tail": tail,
                "fpattern": fpattern,
                "start": start,
                "end": end,
            }
