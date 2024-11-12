import os
import multiprocessing
import logging


########################################################################
class Environ_:
    """"""
    # ----------------------------------------------------------------------
    def __call__(self, value, default=None):
        """"""
        return os.getenv(value, default)

    # ----------------------------------------------------------------------
    def __getattr__(self, value):
        """"""
        return os.getenv(value, None)


environ = Environ_()


# ----------------------------------------------------------------------
def run_script(script, port):
    """"""
    if os.path.exists(script):
        def worker(script, port):
            os.system(f"python {script} {port}")
        p = multiprocessing.Process(target=worker, args=(script, port))
        p.start()
    else:
        logging.warning(f'{script} not exists')
