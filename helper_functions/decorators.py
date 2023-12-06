"""Module to hold decorators."""
import logging
import time
import traceback
from typing import Any, Callable

from sqlalchemy.exc import DatabaseError, IntegrityError, OperationalError
from sqlalchemy.orm import scoped_session
from urllib3.exceptions import ConnectTimeoutError, ReadTimeoutError


def removes_session(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to remove a scroped session from a Feed object after function call. \
    This decorator also removes the session from the object if an exception is raised.

    Args:
        func (function): Function to wrap.
    Returns:
        function: Wrapped function.
    """

    def _removes_session(*args, **kwargs) -> Any:
        """Wrapper for decorator. Removes session from Feed object after function call."""
        try:
            res = func(*args, **kwargs)
        except (
            OperationalError,
            IntegrityError,
            DatabaseError,
            KeyError,
            TimeoutError,
            ReadTimeoutError,
            ConnectTimeoutError,
        ) as err:
            logging.error("OperationalError: %s", err)
            logging.error(traceback.format_exc())
            res = None
        for arg in args:
            for attr_name in dir(arg):
                attr = getattr(arg, attr_name)
                if isinstance(attr, scoped_session):
                    attr.remove()
        return res

    return _removes_session


def timeit(func: Callable[..., Any], round_to: int = 3) -> Callable[..., Any]:
    """Decorator to time a function and log it.

    Args:
        func (function): Function to wrap.
        round_to (int, optional): Number of decimal places to round to. Defaults to 3.
    Returns:
        function: Wrapped function.
    """

    def _timeit(*args, **kwargs) -> Any:
        """Wrapper for decorator."""
        start = time.perf_counter()
        res = func(*args, **kwargs)
        logging.info(
            "Ran %s in %f s",
            func.__name__,
            round(time.perf_counter() - start, round_to),
        )
        return res

    return _timeit
