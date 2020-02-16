
import logging
from avalon import io
from avalon.vendor import qtawesome
from avalon.tools import lib


main_logger = logging.getLogger("modeldiffer")


schedule = lib.schedule
defer = lib.defer


def icon(name, color=None):
    return qtawesome.icon("fa.{}".format(name), color=color)


profile_from_host = NotImplemented
select_from_host = NotImplemented


def is_supported_loader(name):
    return name in ("ModelLoader", "RigLoader", "LookLoader")


def is_supported_subset(name):
    return any(name.startswith(family)
               for family in ("model", "rig", "look"))


def profile_from_database(subset_id, version_id):
    """
    """
    subset = io.find_one({"_id": subset_id})
    version = io.find_one({"_id": version_id})

    if subset["schema"] == "avalon-core:subset-3.0":
        family = subset["data"]["families"][0]
    else:
        family = version["data"]["families"][0]

    _DATA_GETTER = {
        "model": _get_model_data,
        "rig": _get_rig_data,
        "look": _get_look_data,
    }

    family = family.split(".", 1)[-1]
    getter = _DATA_GETTER[family]

    return getter(version_id)


# (NOTE) The data we need should be stored in `version`,
#        but currently stored in `representation`.
#        Should solved this in future.


def _get_model_data(version_id):
    MODE_DATA = [
        "displayName",
        "avalonId",
        "name",
        "hierarchy",
        "points",
        "uvmap",
        "protected",
    ]

    representation = io.find_one({"type": "representation",
                                  "name": "mayaBinary",
                                  "parent": version_id})
    if representation is None:
        main_logger.critical("Representation not found. This is a bug.")
        return

    model_profile = representation["data"].get("modelProfile")
    model_protected = representation["data"].get("modelProtected", [])

    if model_profile is None:
        main_logger.critical("'data.modelProfile' not found."
                             "This is a bug.")
        return

    profile = dict()

    for id, meshes in model_profile.items():
        # Currently, meshes with duplicated id are not supported,
        # and may remain unsupported in the future.
        data = meshes[0]

        name = data.pop("hierarchy")
        # No need to compare normals
        data.pop("normals")

        data["avalonId"] = id
        data["protected"] = id in model_protected

        profile[name] = data

    return profile


def _get_rig_data(version_id):
    RIG_DATA = [
        "displayName",
        "avalonId",
        "name",
        "hierarchy",
        "points",
        "uvmap",
    ]
    representation = io.find_one({"type": "representation",
                                  "name": "mayaBinary",
                                  "parent": version_id})
    if representation is None:
        main_logger.critical("Representation not found. This is a bug.")
        return

    model_profile = representation["data"].get("modelProfile")

    if model_profile is None:
        main_logger.critical("'data.modelProfile' not found."
                             "This is a bug.")
        return

    profile = dict()

    for id, meshes in model_profile.items():
        # Currently, meshes with duplicated id are not supported,
        # and may remain unsupported in the future.
        data = meshes[0]

        name = data.pop("hierarchy")
        # No need to compare normals
        data.pop("normals")

        data["avalonId"] = id

        profile[name] = data

    return profile


def _get_look_data(version_id):
    RIG_DATA = [
        "displayName",
        "avalonId",  # Not the shader's AvalonId, but the model to match
        "shaderName",
    ]
