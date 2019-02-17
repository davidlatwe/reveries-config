
import os
import tempfile
import hashlib
import codecs
import shutil
import weakref
import getpass
import errno
import pymongo

from avalon import io, Session

import pyblish.api
import avalon
from pyblish_qml.ipc import formatting


def temp_dir(prefix="pyblish_tmp_"):
    """Provide a temporary directory for staging

    This temporary directory is generated through `tempfile.mkdtemp()`

    Arguments:
        prefix (str, optional): Prefix name of the temporary directory

    """
    return tempfile.mkdtemp(prefix=prefix)


def clear_stage(prefix="pyblish_tmp_"):
    """Remove temporary staging directory with prefix

    Remove temporary directory which named with prefix in
    `tempfile.gettempdir()`

    Arguments:
        prefix (str, optional): Prefix name of the temporary directory

    """
    tempdir = tempfile.gettempdir()
    cwd_backup = os.getcwd()

    os.chdir(tempdir)
    for item in os.listdir(tempdir):
        if not (os.path.isdir(item) and item.startswith(prefix)):
            continue

        # Remove
        full_path = os.path.join(tempdir, item)
        print("Removing {!r}".format(full_path))
        shutil.rmtree(full_path)
        print("Removed.")

    os.chdir(cwd_backup)


def get_timeline_data(project=None, asset_name=None):
    """Get asset timeline data from project document

    Get timeline data from asset if asset has it's own settings, or get from
    project.

    Arguments:
        project (dict, optional): Project document, query from database if
            not provided.
        asset_name (str, optional): Asset name, get from `avalon.Session` if
            not provided.

    Returns:
        edit_in (int),
        edit_out (int),
        handles (int),
        fps (float)

    """
    if project is None:
        project = avalon.io.find_one({"type": "project"})
    asset_name = asset_name or avalon.Session["AVALON_ASSET"]
    asset = avalon.io.find_one({"name": asset_name, "type": "asset"})

    assert asset is not None, ("Asset {!r} not found, this is a bug."
                               "".format(asset_name))

    def get(key):
        return asset["data"].get(key, project["data"][key])

    edit_in = get("edit_in")
    edit_out = get("edit_out")
    handles = get("handles")
    fps = get("fps")

    return edit_in, edit_out, handles, fps


def compose_timeline_data(project=None, asset_name=None):
    """Compute and return start frame, end frame and fps

    Get timeline data from asset if asset has it's own settings, or get from
    project.

    Arguments:
        project (dict, optional): Project document, query from database if
            not provided.
        asset_name (str, optional): Asset name, get from `avalon.Session` if
            not provided.

    Returns:
        start_frame (int),
        end_frame (int),
        fps (float)

    """
    edit_in, edit_out, handles, fps = get_timeline_data(project, asset_name)
    start_frame = edit_in - handles
    end_frame = edit_out + handles

    return start_frame, end_frame, fps


def get_resolution_data(project=None):
    """Get resolution data from project

    If resolution data is not defined in project settings, return Full HD res
    (1920, 1080).

    Arguments:
        project (dict, optional): Project document, query from database if
            not provided.

    Returns:
        resolution_width (int),
        resolution_height (int)

    """
    if project is None:
        project = avalon.io.find_one({"type": "project"})
    resolution_width = project["data"].get("resolution_width", 1920)
    resolution_height = project["data"].get("resolution_height", 1080)
    return resolution_width, resolution_height


def init_app_workdir(*args):
    """Wrapped function of app initialize

    Copied from Colorbleed config, modified.
    Useful when changing task context, e.g. on_task_changed

    """

    # Inputs (from the switched session and running app)
    session = avalon.Session.copy()
    app_name = os.environ["AVALON_APP_NAME"]

    # Find the application definition
    app_definition = avalon.lib.get_application(app_name)

    App = type(
        "app_%s" % app_name,
        (avalon.api.Application,),
        {
            "name": app_name,
            "config": app_definition.copy()
        }
    )

    # Initialize within the new session's environment
    app = App()
    env = app.environ(session)
    app.initialize(env)


def override_event(event, callback):
    """Override existing event callback

    Copied from Colorbleed config.

    Args:
        event (str): name of the event
        callback (function): callback to be triggered

    Returns:
        None

    """

    ref = weakref.WeakSet()
    ref.add(callback)

    avalon.pipeline._registered_event_handlers[event] = ref


def publish_results_formatting(context):
    formatted = []
    for result in context.data["results"]:
        formatted.append(formatting.format_result(result))
    return formatted


def hash_file(file_path):
    hasher = AssetHasher()
    hasher.add_file(file_path)
    return hasher.digest()


def plugins_by_range(base=1.5, offset=2, paths=None):
    """Find plugins by thier order which fits in range

    Default param will return plugins that -0.5<=order<3.5, which is standard
    range of Pyblish CVEI.

    -.5 <= C < 0.5
    0.5 <= V < 1.5
    1.5 <= E < 2.5
    2.5 <= I < 3.5

    Arguments:
        base (float): Center of range
        offset (float, optional): Amount of offset from base

    """
    _min = base - offset
    _max = base + offset

    plugins = list()

    for plugin in pyblish.api.discover(paths=paths):
        if ("order" in plugin.__dict__ and
                _min <= plugin.order < _max):

            plugins.append(plugin)

    return plugins


class _C4Hasher(object):

    CHUNK_SIZE = 4096 * 10  # magic number
    PREFIX = "c4"

    def __init__(self):
        self.hash_obj = None
        self.clear()

    def clear(self):
        """Start a new hash session
        """
        self.hash_obj = hashlib.sha512()

    def _b58encode(self, bytes):
        """Base58 Encode bytes to string
        """
        b58chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        b58base = 58

        long_value = int(codecs.encode(bytes, "hex_codec"), 16)

        result = ""
        while long_value >= b58base:
            div, mod = divmod(long_value, b58base)
            result = b58chars[mod] + result
            long_value = div

        result = b58chars[long_value] + result

        return result

    def digest(self):
        """Return hash value of data added so far
        """
        c4_id_length = 90
        b58_hash = self._b58encode(self.hash_obj.digest())

        padding = ""
        if len(b58_hash) < (c4_id_length - 2):
            padding = "1" * (c4_id_length - 2 - len(b58_hash))

        c4id = self.PREFIX + padding + b58_hash
        return c4id


class AssetHasher(_C4Hasher):
    """A data hasher for digital content creation

    This is a Python implemtation of Avalanche-io C4 Asset ID.

    Usage:
        >> hasher = AssetHasher()
        >> hasher.add_file("/path/to/file")
        >> hasher.add_dir("/path/to/dir")

        You can keep adding more assets.
        And get the hash value by
        >> hasher.digest()
        'c463d2Wh5NyBMQRHyxbdBxCzZfaKXvBQaawgfgG18moxQU2jdmaSbCWL...'

        You can still adding more assets at this point
        >> hasher.add_file("/path/to/more/file")

        And get the hash value of all asset added so far
        >> hasher.digest()
        'c43cysVyTd7kYurvAa5ooR6miJJgUZ9QnBCHZeNK3en9aQ96KHsoJyJX...'

        Until you call `clear`
        >> hasher.clear()

    """

    def add_file(self, file_path):
        """Add one file to hasher

        Arguments:
            file_path (str): File path string

        """
        chunk_size = self.CHUNK_SIZE

        with open(file_path, "rb") as file:
            for chunk in iter(lambda: file.read(chunk_size), b""):
                self.hash_obj.update(chunk)

    def add_dir(self, dir_path, recursive=True, followlinks=True):
        """Add one directory to hasher

        Arguments:
            dir_path (str): Directory path string
            recursive (bool, optional): Add sub-dir as well, default is True
            followlinks (bool, optional): Add directories pointed to by
                symlinks, default is True

        """
        for root, dirs, files in os.walk(dir_path, followlinks=followlinks):
            for name in files:
                self.add_file(os.path.join(root, name))

            if not recursive:
                continue

            for name in dirs:
                path = os.path.join(root, name)
                self.add_dir(path, recursive=True, followlinks=followlinks)


def get_representation_path_(representation, parents):
    """Get filename from representation document

    Decoupled from `avalon.pipeline.get_representation_path`

    Args:
        representation (dict): representation document from the database
        parents (list): Documents returned from `io.parenthood`

    Returns:
        str: fullpath of the representation

    """
    version, subset, asset, project = parents
    template_publish = project["config"]["template"]["publish"]
    return template_publish.format(**{
        "root": avalon.api.registered_root(),
        "project": project["name"],
        "asset": asset["name"],
        "silo": asset["silo"],
        "subset": subset["name"],
        "version": version["name"],
        "representation": representation["name"],
        "user": avalon.api.Session.get("AVALON_USER", getpass.getuser()),
        "app": avalon.api.Session.get("AVALON_APP", ""),
        "task": avalon.api.Session.get("AVALON_TASK", "")
    })


def deep_update(d, update):
    """Recursively update dict value"""
    for k, v in update.items():
        if isinstance(v, dict):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


class AssetGraber(object):
    """Copy asset and it's dependencies to another project

    This is used for copying asset representation and all it's dependency
    assets from current project to another project.

    Example:
        >>> # Init with the name of the destination project
        >>> graber = AssetGraber("other_project")
        >>> # Input representation ID
        >>> graber.grab("5c6159dbed9f0d0509a34e27")
        >>> # Grab another...
        >>> graber.grab("5c6159dbed9f0d0509a34e38")

    """

    def __init__(self, project):
        self.project = project
        self._project = None
        self._mongo_client = None
        self._database = None
        self._collection = None
        self._connected = False

    def grab(self, representation_id):
        """Copy representation to project

        Args:
            representation_id (str or ObjectId): representation id

        """
        if not self._connected:
            self._connect()
        if isinstance(representation_id, str):
            representation_id = io.ObjectId(representation_id)
        self._copy_representations(representation_id)

    def _connect(self):
        timeout = int(Session["AVALON_TIMEOUT"])
        self._mongo_client = pymongo.MongoClient(
            Session["AVALON_MONGO"], serverSelectionTimeoutMS=timeout)
        self._database = self._mongo_client[Session["AVALON_DB"]]
        self._collection = self._database[self.project]
        self._connected = True

        self._project = self._find_one({"type": "project"})

    def _insert_one(self, item):
        assert isinstance(item, dict), "item must be of type <dict>"
        return self._collection.insert_one(item)

    def _find_one(self, filter, projection=None, sort=None):
        assert isinstance(filter, dict), "filter must be <dict>"
        return self._collection.find_one(
            filter=filter,
            projection=projection,
            sort=sort
        )

    def _copy_representations(self, representation_id):
        """Copy all documents and files of representation and dependencies"""
        # Representation
        representation = self._find_one({"_id": representation_id})
        if not representation:
            representation = io.find_one({"_id": representation_id})
            self._insert_one(representation)

            # Version
            version = io.find_one({"_id": representation["parent"]})
            if not self._find_one({"_id": version["_id"]}):
                self._insert_one(version)

                # Subset
                subset = io.find_one({"_id": version["parent"]})
                if not self._find_one({"_id": subset["_id"]}):
                    self._insert_one(subset)

                    # Asset
                    asset = io.find_one({"_id": subset["parent"]})
                    if not self._find_one({"_id": asset["_id"]}):
                        asset["parent"] = self._project["_id"]
                        self._insert_one(asset)

                        # Asset Visual Parent
                        parent_id = asset["data"]["visualParent"]
                        if parent_id:
                            parent_id = io.ObjectId(parent_id)
                            if not self._find_one({"_id": parent_id}):
                                parent_asset = io.find_one({"_id": parent_id})
                                parent_asset["parent"] = self._project["_id"]
                                self._insert_one(parent_asset)

                # Dependencies
                for dependency_id in version["data"]["dependencies"]:
                    dependency_id = io.ObjectId(dependency_id)
                    for representation_ in io.find({"parent": dependency_id}):
                        self._copy_representations(representation_["_id"])

        # Copy package
        parents = io.parenthood(representation)
        src_package = get_representation_path_(representation, parents)
        parents = parents[:-1] + [self._project]
        dst_package = get_representation_path_(representation, parents)
        self._copy_dir(src_package, dst_package)

    def _copy_dir(self, src, dst):
        """ Copy given source to destination"""
        try:
            shutil.copytree(src, dst)
        except OSError as e:
            if e.errno == errno.EEXIST:
                print("Representation dir existed.")
            else:
                raise OSError("An unexpected error occurred.")
