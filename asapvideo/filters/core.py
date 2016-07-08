from random import random

"""
    Filter expressions accessor
"""
class FilterExpressionAccessor(object):
    def __init__(self, expressions, random = False):
        self._expressions = expressions
        self._random = random
    
    def get_expression(self, iteration):
        if self._expressions == 0:
            return None
        elif self._expressions == 1:
            return self._expressions[0]
        elif self._random == True:
            return self._randomize(iteration)
        else:
            return self._alternate(iteration)
        
    def _alternate(self, iteration):
        return self._expressions[iteration % len(self._expressions)]

    def _randomize(self, iteration):
        random.shuffle(self._expressions)
        return next(iter(self._expressions))

"""
    Combining expressions accessor
"""
class CombiningExpressionAccessor(FilterExpressionAccessor):
    def __init__(self, accessors):
        self._accessors = accessors
    
    def get_expression(self, iteration):
        return ",".join([a.get_expression(iteration) for a in self._accessors])

"""
    Base class for filters
"""
class Filter(object):
    def __init__(self, outstreamprefix):
        self._outstreamprefix = outstreamprefix

    def generate(self, streams):
        raise NotImplementedError("Subclasses should implement this!")

    def _generate_base(self, streams, expression_accessor):
        i = 0
        newstreams = []
        output = []
        for s in streams:
            newstream = self._outstreamprefix
            if i > 0: newstream += str(i)
            output.append("[{s}]{e}[{ns}]".format(s = s, e = expression_accessor.get_expression(i), ns = newstream))
            newstreams.append(newstream)
            i += 1
        return output, newstreams


"""
    Base class for combinable objects
"""
class Combinable(object):
    def __init__(self, accessor):
        self._accessor = accessor

    def get_accessor(self):
        return self._accessor


"""
    Combining filter
"""
class CombiningFilter(Filter, Combinable):
    def __init__(self, combinables, outstreamprefix):
        Filter.__init__(self, outstreamprefix)
        Combinable.__init__(self, CombiningExpressionAccessor([c.get_accessor() for c in combinables]))

    def generate(self, streams):
        return self._generate_base(streams, self.get_accessor())


"""
    Duration filter
"""
class DurationFilter(Filter, Combinable):
    def __init__(self, duration, outstreamprefix="df"):
        Filter.__init__(self, outstreamprefix)
        Combinable.__init__(self, FilterExpressionAccessor([
            "trim=duration={dt}".format(dt = duration)
        ]))

    def generate(self, streams):
        return self._generate_base(streams, self.get_accessor())


"""
    Scale filter
"""
class ScaleFilter(Filter, Combinable):
    def __init__(self, width, height, outstreamprefix="scf"):
        Filter.__init__(self, outstreamprefix)
        Combinable.__init__(self, FilterExpressionAccessor([
            "scale={w}:{h}".format(w = width, h = height)
        ]))

    def generate(self, streams):
        return self._generate_base(streams, self.get_accessor())


"""
    SAR and PTS filter
"""
class SARPTSFilter(Filter, Combinable):
    def __init__(self, outstreamprefix="sptf"):
        Filter.__init__(self, outstreamprefix)
        Combinable.__init__(self, FilterExpressionAccessor([
            "setsar=1:1,setpts=PTS-STARTPTS"
        ]))

    def generate(self, streams):
        return self._generate_base(streams, self.get_accessor())


"""
    Basic image slide filter
"""
class ImageSlideFilter(CombiningFilter):
    def __init__(self, duration, width, height, outstreamprefix="isf"):
        CombiningFilter.__init__(self, [DurationFilter(duration), ScaleFilter(width, height), SARPTSFilter()], outstreamprefix)


"""
    Media concat filter
"""
class ConcatFilter(Filter):
    def __init__(self, is_video, outputtag):
        super(self.__class__, self).__init__(outstreamprefix = outputtag)
        self._is_video = is_video
        self._outputtag = outputtag

    def generate(self, streams):
        tags = "".join(["[%s]" % s for s in streams])
        return  ["{t}concat=n={c}:v={vo}:a={ao}[{ot}]".format(
            t=tags, 
            c=len(streams),
            vo = 1 if self._is_video == True else 0,
            ao = 1 if self._is_video == False else 0,
            ot=self._outputtag)
        ], [self._outputtag]


"""
    Chain of filters executed sequentially
"""
class FilterChain(Filter):
    def __init__(self, filters = []):
        self._filters = filters

    def append(self, filter):
        self._filters.append(filter)

    def generate(self, streams):
        output = []
        newstreams = streams
        for f in self._filters:
            res = f.generate(newstreams)
            output += res[0]
            newstreams = res[1]
        return output, newstreams

"""
    Video split filter
"""
class VideoSplitFilter(Filter):
    def __init__(self, count, outstreamprefix = "vsf"):
        super(self.__class__, self).__init__(outstreamprefix = outstreamprefix)
        self._count = count
        self._names = ['a', 'b', 'b', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'x', 'y', 'z']

    def generate(self, streams):
        output = []
        newstreams = []
        for s in streams:
            new = [self._outstreamprefix + self._names[i] for i in range(0,self._count)]
            newstreams += new
            output.append("[{s}]split={c}{ns}".format(
                s = s,
                c = self._count,
                ns = "".join(["[%s]" % ns for ns in new])
            ))
        return output, newstreams