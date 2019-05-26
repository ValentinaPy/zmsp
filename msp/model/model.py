#
from msp.nn import BK
from msp.utils import zlog

# A model tells all the story
class Model(object):
    # list(mini-batch) of to-decode instances,
    # results are written in-place, return info.
    def inference_on_batch(self, insts):
        raise NotImplementedError()

    # list(mini-batch) of annotated instances
    # optional results are written in-place? return info.
    def fb_on_batch(self, annotated_insts, training=True):
        raise NotImplementedError()

    # called before each mini-batch
    def refresh_batch(self, training):
        raise NotImplementedError()

    # called for one step of paramter-update
    def update(self, lrate):
        raise NotImplementedError()

    # get all values need to be schedules, like lrate
    def get_scheduled_values(self):
        raise NotImplementedError()

    # load model conf & params
    def load(self, path):
        raise NotImplementedError()

    # save model conf & params
    def save(self, path):
        raise NotImplementedError()
