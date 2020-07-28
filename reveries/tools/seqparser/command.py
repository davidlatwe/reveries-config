
import os
import json
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


CACHE_FILE_NAME = ".sequences.json"


def save_cache(cache,
               output_dir,
               padding_string,
               start,
               end,
               is_stereo,
               is_single,
               created_by):
    data = {
        "cache": cache,
        "paddingStr": padding_string,
        "start": start,
        "end": end,
        "isStereo": is_stereo,
        "isSingle": is_single,
        "createdBy": created_by,
    }
    file_path = os.path.join(output_dir, CACHE_FILE_NAME)
    with open(file_path, "w") as fp:
        json.dump(data, fp, indent=4, sort_keys=True)


def load_cache(dir_path):
    file_path = os.path.join(dir_path, CACHE_FILE_NAME)
    if not os.path.isfile(file_path):
        return

    with open(file_path, "r") as fp:
        data = json.load(fp)

    return data
