import sys


class fake:
    def __init__(self, *args, **kwargs):
        """"""

    def __getattr__(self, attr):
        if attr in globals():
            return globals()[attr]
        else:
            return fake


brython = ['browser',
           'browser.template',
           'browser.html',
           'interpreter',
           'browser.local_storage',
           ]
for module in brython:
    sys.modules[f"{module}"] = fake()

modules = ['sound',
           'icons',
           'framework',
           'framework.sound',
           ]
for module in modules:
    sys.modules[f"radiant.{module}"] = fake()
