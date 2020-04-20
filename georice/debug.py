import functools
import logging
import time

logging.basicConfig(filename=r"C:\Users\micha\PycharmProjects\GEO\georice\\georice\\file.log", level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(funcName)s:%(message)s')


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


class LogDecorator(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.count = 1

    def __call__(self, fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            try:
                start = time.perf_counter()
                result = fn(*args, **kwargs)
                end = time.perf_counter()
                msg = f'Function {fn.__name__} finished in {end-start:.4f}s, func call no:{decorated.count}'
                self.logger.info(msg)
                decorated.count += 1
                return result
            except Exception as ex:
                self.logger.debug("Exception {0}".format(ex))
                raise ex
        decorated.count = 1
        return decorated

# def counter(original):
#     def counter(*args, **kwargs):
#         msg = f'{original.__name__} {counter.call}'
#         logging.DEBUG(msg)
#         print(msg)
#         counter.call += 1
#         return original(*args, **kwargs)
#     counter.call = 1
#     return counter
#
#
# def timer(func):
#     """Print the runtime of the decorated function"""
#     @functools.wraps(func)
#     def wrapper_timer(*args, **kwargs):
#         start = time.perf_counter()
#         value = func(*args, **kwargs)
#         end = time.perf_counter()
#         msg = f'{datetime.now().isoformat()}:Function {func.__name__} finished in {end-start:.4f} s'
#         logging.DEBUG(msg)
#         print(msg)
#         return value
#     return wrapper_timer
#
# def timer_counter(func):
#     """Print the runtime of the decorated function"""
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         start = time.perf_counter()
#         value = func(*args, **kwargs)
#         end = time.perf_counter()
#         msg = f'{datetime.now().isoformat()}:Function {func.__name__} finished in {end-start:.4f} : call no: {wrapper.call}s'
#         logging.info(msg)
#         print(msg)
#         wrapper.call += 1
#         return value
#     wrapper.call = 1
#     return wrapper

import os, json, click

def load_config():
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.isfile(config_file):
        raise IOError('Configuration file does not exist: %s' % os.path.abspath(config_file))
    with open(config_file, 'r') as cfg_file:
        return json.load(cfg_file)

config = load_config()
config_rice = load_config()

period, orb_num, orb_path = set(), set(), set()
scn_path = config_rice['scn_output']
with os.scandir(config_rice['scn_output']) as files:
    for file in files:
        if file.is_file():
            parsed = file.name.split('_')
            period.add(parsed[5])
            orb_num.add(int(parsed[4]))
            orb_path.add(parsed[3])

print(files)