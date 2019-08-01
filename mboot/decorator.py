import sys
import logging
import traceback
import functools

def global_error_handler(func):
    @functools.wraps(func)
    def warpper():
        try:
            func()
        except Exception as e:
            root_logger = logging.getLogger()
            err_msg = '\n' + traceback.format_exc() if root_logger.level == logging.DEBUG else ' ERROR: {}'.format(str(e))
            print(err_msg)
            sys.exit(0)
    return warpper
