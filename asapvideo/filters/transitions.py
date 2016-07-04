from enum import IntEnum
from core import Filter, FilterExpressionsAccessor

"""
    Base transition filter class
"""
class TransitionFilter(Filter):
    def needs_prev_slide(self):
        raise NotImplementedError("Subclasses should implement this!")


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
    Slide transition filter builder
"""
class SlideTransitionFilter(TransitionFilter):
    def __init__(self, transition_duration, preserve_first, direction = SlideTransitionType.alternate, outstreamprefix="stf"):
        super(self.__class__, self).__init__(outstreamprefix)
        expressions = []
        if isinstance(direction, SlideTransitionType) == False:
            direction = SlideTransitionType.alternate
        if direction & SlideTransitionType.left_right == SlideTransitionType.left_right:
            expressions.append("overlay=x='min(-w+(t*w/{td})\,0)':shortest=1".format(td = transition_duration))
        if direction & SlideTransitionType.top_bottom == SlideTransitionType.top_bottom:
            expressions.append("overlay=y='min(-h+(t*h/{td})\,0)':shortest=1".format(td = transition_duration))
        if direction & SlideTransitionType.right_left == SlideTransitionType.right_left:
            expressions.append("overlay=x='max(w-(t*w/{td})\,0)':shortest=1".format(td = transition_duration))
        if direction & SlideTransitionType.bottom_top == SlideTransitionType.bottom_top:
            expressions.append("overlay=y='max(h-(t*h/{td})\,0)':shortest=1".format(td = transition_duration))
        self._expressions_accessor = FilterExpressionsAccessor(expressions, direction == SlideTransitionType.random)
        self._preserve_first = preserve_first

    def generate(self, streams):
        newstreams = []
        split_from_inx = 0 if self._preserve_first == True else 1
        splits = dict([(s, (s+"a", s+"b")) for s in streams[split_from_inx:len(streams)-1]])
        output = ["[{k}]split[{va}][{vb}]".format(k = k, va = v[0], vb = v[1]) for (k, v) in splits.iteritems()]
        sprev = streams[0]
        i = 0
        if self._preserve_first == True: newstreams.append(splits[streams[0]][0])
        for s in streams[1:]:
            splitprev = splits[sprev] if sprev in splits else None
            split = splits[s] if s in splits else None
            newstream = self._outstreamprefix
            if i > 0: newstream += str(i)
            output.append(
                "[{b}][{o}]{e}[{ns}]"
                .format(
                    b = splitprev[1] if splitprev else sprev, 
                    o = split[0] if split else s,
                    e = self._expressions_accessor.get_expression(i),
                    ns = newstream)
            )
            newstreams.append(newstream)
            sprev = s
            i += 1
        return output, newstreams

    def needs_prev_slide(self):
        return True


"""
    Fade in/out transition filter builder
"""
class FadeTransitionFilter(TransitionFilter):
    def __init__(self, transition_duration, total_duration, outstreamprefix="ftf"):
        super(self.__class__, self).__init__(outstreamprefix)
        self._expressions_accessor = FilterExpressionsAccessor([
            "fade=t=in:st=0:d={tt},fade=t=out:st={te}:d={tt}".format(tt = transition_duration, te = total_duration - transition_duration)
        ])

    def generate(self, streams):
        return self._generate_base(streams, self._expressions_accessor)

    def needs_prev_slide(self):
        return False