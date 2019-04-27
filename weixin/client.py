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
    """

    def __init__(
        self,
        *,
        mode: str = 'async',
        path: str = '',
        loop: Optional[asyncio.AbstractEventLoop] = None,
        **kwargs
    ):
        self._mode = mode
        self._path = path
        self._loop = loop or asyncio.get_event_loop()
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
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path

    def __getattr__(self, path):
        self._path = "{}/{}".format(self._path, path)
        return self

    def __str__(self):
        return self._path

    __call__ = __getattr__

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
