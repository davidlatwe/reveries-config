
import sys
import argparse
import pyblish.api
import pyblish_qml.api
import avalon.api
from avalon import style
from avalon.tools import lib as tools_lib
from avalon.tools.creator import app as creator
from reveries import filesys, plugins
from . import app


def publish(sequences):
    """Run sequence publish

    Step:
        1. Press "Accept" after sequences scavenged
        2. Pop-up Avalon Creator, fill in Asset and Subset
        3. Press "Create"
        4. Run Pyblish if no error raised on create (close creator)
        5. Check publish result after Pyblish server stopped
        6. Close all window if completed or raise seqparser window

    Args:
        sequences:

    Returns:

    """
    avalon.api.install(filesys)
    pyblish.api.register_target("localhost")
    pyblish.api.register_target("seqparser")

    filesys.new()

    with tools_lib.application():
        seqparser_app = app.window
        created = {"_": False}

        window = creator.Window(parent=seqparser_app)

        # (NOTE) override `window.on_create`, this is a hack !
        def on_create_hack():
            filesys.put_data("renderCreatorData", {
                "sequences": sequences,
                "isStereo": seqparser_app.is_stereo,
                "stagingDir": seqparser_app.get_root_path(),
            })
            try:
                window.on_create()
            except Exception:
                pass
            else:
                created["_"] = True
                window.close()

        window.data["Create Button"].clicked.disconnect()
        window.data["Subset"].returnPressed.disconnect()
        window.data["Create Button"].clicked.connect(on_create_hack)
        window.data["Subset"].returnPressed.connect(on_create_hack)

        window.setStyleSheet(style.load_stylesheet())
        window.refresh()
        window.exec()

    if not created["_"]:
        raise Exception("Nothing created.")

    seqparser_app.hide()

    server = pyblish_qml.api.show()
    server.wait()

    context = server.service._context
    if not context.data.get("publishSucceed"):
        seqparser_app.show()
        again = plugins.message_box_warning("Nothing published",
                                            "Nothing published, try again ?",
                                            optional=True,
                                            parent=seqparser_app)
        if again:
            raise Exception("Nothing published.")

    seqparser_app.close()


if __name__ == "__main__":
    callback = None
    with_keys = None

    parser = argparse.ArgumentParser(
        prog="Sequences parser [host:filesys]",
        description="Collect image sequences from file system"
    )

    parser.add_argument("-p", "--publish",
                        action="store_true",
                        help="Run Pyblish.")

    args = parser.parse_args(sys.argv[1:])

    if args.publish:
        callback = publish
        with_keys = ["name"]  # Must publish with AOV names

    sys.exit(app.show(callback=callback, with_keys=with_keys))
