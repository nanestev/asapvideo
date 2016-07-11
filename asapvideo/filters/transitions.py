import math
from enum import IntEnum
from core import Filter, FilterExpressionAccessor, Combinable, VideoSplitFilter, CombiningFilter, ImageSlideFilter, ConcatFilter
from effects import ZoompanEffectFilter
from utils import pairwise

"""
    Fade in/out transition filter builder
"""
class FadeTransitionFilter(Filter, Combinable):
    def __init__(self, transition_duration, total_duration, outstreamprefix="ftf"):
        Filter.__init__(self, outstreamprefix)
        Combinable.__init__(self, FilterExpressionAccessor([
            "fade=t=in:st=0:d={tt},fade=t=out:st={te}:d={tt}".format(tt = transition_duration, te = total_duration - transition_duration)
        ]))

    def generate(self, streams):
        return self._generate_base(streams, self.get_accessor())


"""
    Slide transitions types
"""
class SlideTransitionType(IntEnum):
    left_right = (1 << 1),
    right_left = (1 << 2),
    top_bottom = (1 << 3),
    bottom_top = (1 << 4),
    horizontal_alternate = (left_right[0] | right_left[0]),
    vertical_alternate = (top_bottom[0] | bottom_top[0]),
    alternate = (horizontal_alternate[0] | vertical_alternate[0]),
    random = (alternate[0] | 1 << 0)


"""
    Sliding overlay filter
"""
class SlidingOverlayFilter(Filter):
    def __init__(self, transition_duration, type = SlideTransitionType.alternate, outstreamprefix="stf"):
        super(self.__class__, self).__init__(outstreamprefix)
        expressions = []
        if isinstance(type, SlideTransitionType) == False:
            type = SlideTransitionType.alternate
        if type & SlideTransitionType.left_right == SlideTransitionType.left_right:
            expressions.append("overlay=x='min(-w+(t*w/{td})\,0)':shortest=1".format(td = transition_duration))
        if type & SlideTransitionType.top_bottom == SlideTransitionType.top_bottom:
            expressions.append("overlay=y='min(-h+(t*h/{td})\,0)':shortest=1".format(td = transition_duration))
        if type & SlideTransitionType.right_left == SlideTransitionType.right_left:
            expressions.append("overlay=x='max(w-(t*w/{td})\,0)':shortest=1".format(td = transition_duration))
        if type & SlideTransitionType.bottom_top == SlideTransitionType.bottom_top:
            expressions.append("overlay=y='max(h-(t*h/{td})\,0)':shortest=1".format(td = transition_duration))
        self._expressions_accessor = FilterExpressionAccessor(expressions, type == SlideTransitionType.random)
        
    def generate(self, streams):
        newstreams = []
        output = []
        i = 0
        for s1, s2 in pairwise(streams):
            newstream = self._outstreamprefix
            if i > 0: newstream += str(i)
            output.append(
                "[{b}][{o}]{e}[{ns}]".format(
                    b = s1, 
                    o = s2,
                    e = self._expressions_accessor.get_expression(i),
                    ns = newstream)
            )
            newstreams.append(newstream)
            i += 1
        return output, newstreams


"""
    Slide transition filter builder
"""
class SlideTransitionFilter(Filter):
    def __init__(self, transition_duration, preserve_first, type = SlideTransitionType.alternate, outstreamprefix="stf"):
        super(self.__class__, self).__init__(outstreamprefix)
        self._type = type
        self._preserve_first = preserve_first
        self._transition_duration = transition_duration

    def generate(self, streams):
        newstreams = []
        output = []
        splits = {}
        split_from_inx = 0 if self._preserve_first == True else 1
        for s in streams[split_from_inx:len(streams)-1]:
            splitted = VideoSplitFilter(2, outstreamprefix=s.replace(":", "")).generate([s])
            splits[s] = tuple(splitted[1])
            output += splitted[0]
        sprev = streams[0]
        i = 0
        if self._preserve_first == True: newstreams.append(splits[streams[0]][0])
        slides = []
        for s in streams[1:]:
            splitprev = splits[sprev] if sprev in splits else None
            split = splits[s] if s in splits else None
            slides.append(splitprev[1] if splitprev else sprev)
            slides.append(split[0] if split else s)
            sprev = s
        trans = SlidingOverlayFilter(self._transition_duration, self._type).generate(slides)
        return output + trans[0], newstreams + trans[1]


"""
    Class that renders zoompan plus slide in transition filters
"""
class ZoompanSlideInTransitionFilter(Filter):
    def __init__(self, transition_duration, total_duration, fps, width, height, maxzoom, preserve_first, type = SlideTransitionType.alternate, outstreamprefix="ftf"):
        Filter.__init__(self, outstreamprefix)
        self._transition_duration = transition_duration
        self._total_duration = total_duration
        self._width = width
        self._height = height
        self._maxzoom = maxzoom
        self._slide_duration = total_duration - transition_duration
        self._frames = int(math.ceil(self._slide_duration * fps))
        self._preserve_first = preserve_first
        self._type = type

    def generate(self, streams):
        output = []
        newstreams = []
        transitions = []
        parts = []

        s = streams[0]
        if self._preserve_first == True:
            splitted = VideoSplitFilter(3, outstreamprefix = s.replace(":", "")).generate([s])
            output += splitted[0]
            a = ImageSlideFilter(self._transition_duration, self._width, self._height, splitted[1][0] + "z").generate(splitted[1][0:1])
            output += a[0]
            b = CombiningFilter([ZoompanEffectFilter(self._maxzoom, self._frames), ImageSlideFilter(self._slide_duration, self._width, self._height)], splitted[1][1] + "z").generate(splitted[1][1:2])
            output += b[0]
            c = CombiningFilter([ZoompanEffectFilter(self._maxzoom, 1), ImageSlideFilter(self._transition_duration, self._width, self._height)], splitted[1][2] + "z").generate(splitted[1][2:3])
            output += c[0]
            prev = (a[1][0], b[1][0], c[1][0])
            newstreams += [a[1][0], b[1][0]]
        else:                       
            c = CombiningFilter([ZoompanEffectFilter(self._maxzoom, 1), ImageSlideFilter(self._transition_duration, self._width, self._height)], s.replace(":", "") + "z").generate([s])
            output += c[0]
            prev = (c[1][0], c[1][0], c[1][0])

        for s in streams[1:]:
            splitted = VideoSplitFilter(3, outstreamprefix = s.replace(":", "")).generate([s])
            output += splitted[0]
            a = ImageSlideFilter(self._transition_duration, self._width, self._height, splitted[1][0] + "z").generate(splitted[1][0:1])
            output += a[0]
            b = CombiningFilter([ZoompanEffectFilter(self._maxzoom, self._frames), ImageSlideFilter(self._slide_duration, self._width, self._height)], splitted[1][1] + "z").generate(splitted[1][1:2])
            output += b[0]
            c = CombiningFilter([ZoompanEffectFilter(self._maxzoom, 1), ImageSlideFilter(self._transition_duration, self._width, self._height)], splitted[1][2] + "z").generate(splitted[1][2:3])
            output += c[0]
            transitions += [prev[2], a[1][0]]
            parts.append([b[1][0]])
            prev = (a[1][0], b[1][0], c[1][0])

        parts[-1].append(prev[2])
        tran = SlidingOverlayFilter(self._transition_duration, self._type, "t").generate(transitions)
        output += tran[0]
        t = iter(tran[1])
        for p in parts:
            newstreams.append(next(t))
            newstreams += p
        return output, newstreams