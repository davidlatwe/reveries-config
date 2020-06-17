
import sys
import argparse
import avalon.api
import pyblish.api
import pyblish.util
from reveries import filesys, lib


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="Pyblish [host:filesys]",
                                     description="Run publish on file system")

    parser.add_argument("-d", "--dump",
                        type=str,
                        default="",
                        help="Context or Instance dump file path.")
    parser.add_argument("-p", "--progress",
                        type=int,
                        default=0,
                        help="Publish progress, e.g. processed frame count.")
    parser.add_argument("-o", "--progress-output",
                        type=str,
                        nargs="*",
                        help="Progressive publish output file abs path.")
    parser.add_argument("-D", "--Deadline-support",
                        action="store_true",
                        help="Prefix error message to trigger job fail.")

    data = dict()
    args = parser.parse_args(sys.argv)

    if args.dump:
        data["_pyblishDumpFile"] = args.dump

    if args.progress:
        data["_progressivePublishing"] = args.progress

    if args.progress_output:
        data["_progressiveOutput"] = args.progressive

    error_prefix = ""
    if args.Deadline_support:
        error_prefix = "Fatal Error: "

    # Run

    avalon.api.install(filesys)
    pyblish.api.register_target("localhost")

    context = pyblish.util.publish()
    context.data.update(data)

    lib.publish_remote(context, error_prefix)
