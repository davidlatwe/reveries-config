import pyblish.api


class ValidateCommentInputted(pyblish.api.ContextPlugin):
    """發佈時務必打註解

    跪求懶人包，讓大家知道這個版本的發佈原因是什麼。

    """

    """One must say something before publish
    """

    label = "檢查發佈註解"
    order = pyblish.api.ValidatorOrder - 0.49995

    def process(self, context):
        project = context.data["projectDoc"]
        allow_no_comment = project["data"].get("allowNoComment")
        if allow_no_comment:
            self.log.info("允許無註解發佈..")
            return

        comment = context.data["comment"].strip()
        assert comment, "請寫發佈註解。"
