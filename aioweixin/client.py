# -*- coding: utf-8 -*-


import aiohttp
import asyncio

from typing import Optional
from functools import wraps


__all__ = ('runner', 'Client')


def runner(coro):
    """函数执行包装器"""

    @wraps(coro)
    def inner(self, *args, **kwargs):
        if self.mode == 'async':
            return coro(self, *args, **kwargs)
        return self._loop.run_until_complete(coro(self, *args, **kwargs))

    return inner


class Client(object):
    """
    基础客户端

    基本的使用形式

    ::

        async with Client() as client:
            async with client.session.get('url', params={"user_id": 1}) as resp:
                print(await resp.text())

    :param mode: 运行模式

        - ``async``: 默认模式，非阻塞
        - ``blocking``: 同步阻塞模式

    :param path: event loop

    """

    def __init__(
        self,
        *,
        mode: str = 'async',
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **kwargs
    ):
        self._mode = mode
        self._loop = loop or asyncio.get_event_loop()
        self._session = None
        self.opts = kwargs

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode):
        if mode not in ('async', 'blocking'):
            raise ValueError('Invalid running mode')
        self._mode = mode

    @property
    def session(self):
        if self._session is None:
            self._session = self.create_session(**self.opts)
        return self._session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __del__(self):
        if not self._loop.is_closed() and self._session:
            asyncio.ensure_future(self._session.close(), loop=self._loop)

    @runner
    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    def create_session(self, **kwargs):
        return aiohttp.ClientSession(**kwargs, loop=self._loop)
