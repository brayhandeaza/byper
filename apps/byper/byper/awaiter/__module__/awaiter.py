import asyncio
import functools
import inspect
from typing import Callable, Awaitable, Any, Iterable, TypeVar, ParamSpec, Union
from byper.awaiter.__module__ import AwaiterModule

R = TypeVar("R")
P = ParamSpec("P")


class __Awaiter__(AwaiterModule):
    @classmethod
    def wait(cls, delay: int = 0):
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, AwaiterModule]:
            @functools.wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> AwaiterModule:
                def executor(resolve, reject):
                    async def run():
                        try:
                            if delay > 0:
                                await asyncio.sleep(delay / 1000)
                            result = func(*args, **kwargs)
                            if inspect.isawaitable(result):
                                result = await result
                            resolve(result)
                        except Exception as e:
                            reject(e)
                    asyncio.ensure_future(run())
                return AwaiterModule(executor)
            return wrapper
        return decorator

    @classmethod
    def all(cls, *awaitables: Union[Awaitable[Any], Iterable[Awaitable[Any]]]) -> AwaiterModule:
        if len(awaitables) == 1 and isinstance(awaitables[0], (list, tuple)):
            awaitables = awaitables[0]

        def executor(resolve, reject):
            async def run():
                try:
                    results = await asyncio.gather(*awaitables, return_exceptions=False)
                    resolve(results)
                except Exception as e:
                    reject(e)
            asyncio.create_task(run())

        return AwaiterModule(executor)

    @classmethod
    def done(cls, value: Any) -> AwaiterModule:
        return AwaiterModule(lambda resolve, _: resolve(value))

    @classmethod
    def error(cls, error: Exception) -> AwaiterModule:
        return AwaiterModule(lambda _, reject: reject(error))
