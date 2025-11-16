import time
from typing import Callable, Dict
from .models import ActionCall, ActionResult

class ActionExecutor:
    def __init__(self, policy, registry: Dict[str, Callable]):
        self.policy = policy
        self.registry = registry

    def execute(self, call: ActionCall) -> ActionResult:
        t0 = time.perf_counter()
        try:
            self.policy.check(call)
        except Exception as e:
            dt = int((time.perf_counter() - t0) * 1000)
            return ActionResult(success=False, error=str(e), duration_ms=dt)
        fn = self.registry.get(call.name)
        if not fn:
            dt = int((time.perf_counter() - t0) * 1000)
            return ActionResult(success=False, error=f"Unknown action {call.name}", duration_ms=dt)
        try:
            result = fn(**call.params)
            if isinstance(result, ActionResult):
                result.duration_ms = int((time.perf_counter() - t0) * 1000)
                return result
            dt = int((time.perf_counter() - t0) * 1000)
            return ActionResult(success=True, data={"result": result}, duration_ms=dt)
        except Exception as e:
            dt = int((time.perf_counter() - t0) * 1000)
            return ActionResult(success=False, error=str(e), duration_ms=dt)