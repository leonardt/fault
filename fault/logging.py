from __future__ import absolute_import
from __future__ import print_function

import logging
import traceback
import inspect
import sys


log = logging.getLogger("fault")


def info(message, *args, **kwargs):
    log.info(message, *args, **kwargs)


def debug(message, *args, **kwargs):
    log.debug(message, *args, **kwargs)


def warning(message, *args, **kwargs):
    log.warning(message, *args, **kwargs)


def error(message, *args, **kwargs):
    log.error(message, *args, **kwargs)
