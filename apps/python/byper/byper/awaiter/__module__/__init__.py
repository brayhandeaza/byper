import asyncio
from typing import Callable, Any, List, Optional


class AwaiterModule:
    def __init__(self, executor: Callable[[Callable[[Any], None], Callable[[Exception], None]], None]):
        self._executor = executor
        self._then_chain: List[Callable[[Any], Any]] = []
        self._catch: Optional[Callable[[Exception], Any]] = None

    def next(self, callback: Callable[[Any], Any]):
        self._then_chain.append(callback)
        return self

    def error(self, callback: Callable[[Exception], Any]):
        # only set if not already set
        if self._catch is None:
            self._catch = callback
        return self

    def __await__(self):
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def resolve(value):
            if not future.done():
                future.set_result(value)

        def reject(error):
            if not future.done():
                future.set_exception(error)

        try:
            self._executor(resolve, reject)
        except Exception as e:
            reject(e)

        try:
            result = yield from future.__await__()

            # Run .next chain ONLY if no error occurred
            for cb in self._then_chain:
                result = cb(result)
                if asyncio.iscoroutine(result):
                    result = yield from result.__await__()

            return result

        except Exception as e:
            if self._catch:
                try:
                    catch_result = self._catch(e)
                    if asyncio.iscoroutine(catch_result):
                        catch_result = yield from catch_result.__await__()
                    # Stop here. No further `.next` calls.
                    return catch_result
                except Exception as new_e:
                    raise new_e
            else:
                raise e
