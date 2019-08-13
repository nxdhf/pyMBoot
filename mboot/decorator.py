import sys
import time
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

def clock(func):
    '''Used to calculate function time in debug, manually add'''
    @functools.wraps(func)
    def clocked(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        arg_lst = []
        name = func.__name__
        if args:
            arg_lst.append(', '.join(repr(arg) for arg in args))
        if kwargs:
            pairs = ['%s=%r' % (k, w) for k, w in sorted(kwargs.items())]
            arg_lst.append(', '.join(pairs))
        arg_str = ', '.join(arg_lst)
        logging.debug('[%0.8f] %s(%s) -> %r ' % (elapsed, name, arg_str, result))
        return result
    return clocked