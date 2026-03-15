from ..models import ActionResult

def finish_task() -> ActionResult:
    return ActionResult(success=True, data={"status": "finished"})
