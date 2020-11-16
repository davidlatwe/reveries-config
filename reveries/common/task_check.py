def task_check(instance=None, task_name=None):
    from avalon import api
    current_task = api.Session["AVALON_TASK"]

    if str(current_task) != str(task_name):
        return False

    return True
