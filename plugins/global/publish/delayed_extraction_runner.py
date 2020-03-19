
import sys
import traceback
import pyblish.api


class DelayedExtractionRunner(pyblish.api.InstancePlugin):
    """Consume and execute delayed extractors
    """

    order = pyblish.api.ExtractorOrder + 0.49
    label = "Run Delayed Extractions"

    targets = ["localhost"]

    def process(self, instance):
        context = instance.context
        # Skip if any error occurred
        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
            return

        packager = instance.data["packager"]
        for extractor in packager.delayed_extractors():

            repr = extractor["representation"]
            obj = extractor["obj"]
            func = extractor["func"]
            args = extractor["args"]
            kwargs = extractor["kwargs"]

            self.log.info("Running extractor [%s] for [%s] to [%s]..."
                          % (func.__name__, instance, repr))

            try:
                func(obj, *args, **kwargs)
            except Exception as e:
                err_msg = "{file}, line {line}, in {func}: {err}"

                _, _, tb = sys.exc_info()
                last_callstack = traceback.extract_tb(tb)[-1]
                lineno = last_callstack[1]

                errMsg = err_msg.format(file=extractor["obj"].__module__,
                                        line=lineno,
                                        func=func.__name__,
                                        err=str(e))
                self.log.critical(errMsg)
                raise Exception("Extraction failed, see log for deatil.")
            else:
                extractor["_done"] = True
