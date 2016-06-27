__all__ = ['transitions', 'effects']

from random import random
from transitions import *
from effects import *

"""
    Filter expressions accessor
"""
class FilterExpressionsAccessor(object):
    def __init__(self, expressions, random = False):
        self._expressions = expressions
        self._random = random
    
    def get_expression(self, iteration):
        if self._expressions == 0:
            return None
        elif self._expressions == 1:
            return self._expressions[0]
        elif self._random == True:
            return _randomize(iteration)
        else:
            return _alternate(iteration)
        
    def _alternate(self, iteration):
        return self._expressions[iteration % len(self._expressions)]

    def _randomize(self, iteration):
        random.shuffle(self._expressions)
        return next(iter(self._expressions))

"""
    Base class for filters
"""
class Filter(object):

    def generate(self, streams):
        raise NotImplementedError("Subclasses should implement this!")

    def _generate_base(self, streams, newstreamsextension, expressions):
        i = 0
        newstreams = []
        output = []
        for s in streams:
            newstream = s + newstreamsextension
            output.append("[{s}]{e}[{ns}]".format(s = s, e = expressions.get_expression(i), ns = newstream))
            newstreams.append(newstream)
            i += 1
        return output, newstreams


"""
    chain of filters executed sequentially
"""
class FilterChain(object):
    def __init__(self, filters = []):
        self._filters = filters

    def append(self, filter):
        self._filters.append(filter)

    def generate(self, streams):
        output = []
        newstreams = streams
        for f in self._filters:
            res = f.generate(newstreams)
            output.append(res[0])
            newstreams = res[1]
        return output, newstreams


"""
    Basic image slide filter
"""
class ImageSlideFilter(Filter):
    def __init__(self, duration, width, height):
        self._expression_accesor = FilterExpressionsAccessor([
            "trim=duration={dt},scale={w}:{h},setsar=1:1,setpts=PTS-STARTPTS".format(dt = duration, w = width, h = height)
        ])

    def generate(self, streams):
        return self._generate_base(streams, "is", self._expression_accesor)