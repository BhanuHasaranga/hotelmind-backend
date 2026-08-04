import asyncio
import sys

# asyncpg's connection cleanup schedules callbacks on the loop during teardown;
# Windows' default ProactorEventLoop can already be closed by the time that
# runs under pytest-asyncio's per-test event loop, raising "Event loop is
# closed". SelectorEventLoop does not have this issue and is the standard
# workaround for asyncpg + pytest-asyncio on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
