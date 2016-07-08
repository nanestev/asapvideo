import math
from enum import IntEnum
from core import Filter, FilterExpressionAccessor, Combinable, VideoSplitFilter, CombiningFilter, ImageSlideFilter, ConcatFilter
from effects import ZoompanEffectFilter

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
        prev = streams[0]
        i = 0
        for s in streams[1:]:
            newstream = self._outstreamprefix
            if i > 0: newstream += str(i)
            output.append(
                "[{b}][{o}]{e}[{ns}]"
                .format(
                    b = prev, 
                    o = s,
                    e = self._expressions_accessor.get_expression(i),
                    ns = newstream)
            )
            newstreams.append(newstream)
            prev = s
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
        trans = SlidingOverlayFilter(self._transition_duration, self._type, newstream).generate(slides)
        return output + trans[0], newstreams + trans[1]


"""
    Class that renders zoompan plus slide in transition filters
"""
class ZoompanSlideInTransitionFilter(Filter):
    def __init__(self, transition_duration, total_duration, fps, width, height, maxzoom, outstreamprefix="ftf"):
        Filter.__init__(self, outstreamprefix)
        self._transition_duration = transition_duration
        self._total_duration = total_duration
        self._width = width
        self._height = height
        self._maxzoom = maxzoom
        self._frames = int(math.ceil((total_duration - transition_duration) * fps))

    def generate(self, streams):
        output = []
        to_concat = []
        prev = None
        i = 0
        for s in streams:
            splitted = VideoSplitFilter(3, outstreamprefix = s.replace(":", "")).generate([s])
            output += splitted[0]
            a = ImageSlideFilter(self._transition_duration, self._width, self._height).generate(splitted[1][0:0])
            output += a[0]
            b = CombiningFilter([ZoompanEffectFilter(self._maxzoom, self._frames), ImageSlideFilter(self._transition_duration, self._width, self._height)]).generate(splitted[1][1:1])
            output += b[0]
            c = CombiningFilter([ZoompanEffectFilter(self._maxzoom, 1), ImageSlideFilter(self._transition_duration, self._width, self._height)]).generate(splitted[1][2:2])
            output += c[0]
            to_concat += b[1][0]
            if prev:
                tran = SlideTransitionFilter(transition_duration, False, "t" + str(i)).generate([prev[2], a[1][0]])
                output += tran[0]
                to_concat += tran[1][0]
            prev = (a[1][0], b[1][0], c[1][0])
            i += 1
        concatenated = ConcatFilter(True, "v").generate(to_concat)
        output += concatenated[0]
        return output, concatenated[1]


#ffmpeg -y ^
#-loop 1 -i c:\temp\3c575c3d-6fdf-4cc1-a67b-3a61a0459744 ^
#-loop 1 -i c:\temp\aec05d49-18d6-49a8-ad5b-1687628ce9e7 ^
#-loop 1 -i c:\temp\b631229a-ad05-488c-b20c-44b0be01f5de ^
#-filter_complex ^
#"[0:v]split=3[0va][0vb][0vc];^
#[1:v]split=3[1va][1vb][1vc];^
#[2:v]split=3[2va][2vb][2vc];^
#[0va]trim=duration=0.5,scale=792:612,setsar=1:1,setpts=PTS-STARTPTS[0vaz];^
#[0vb]zoompan=z='min(zoom+0.0005,1.0565)':d=113,trim=duration=4.5,scale=792:612,setsar=1:1,setpts=PTS-STARTPTS[0vbz];^
#[0vc]zoompan=z=1.0565:d=1,trim=duration=0.5,scale=792:612,setsar=1:1,setpts=PTS-STARTPTS[0vcz];^
#[1va]trim=duration=0.5,scale=792:612,setsar=1:1,setpts=PTS-STARTPTS[1vaz];^
#[1vb]zoompan=z='min(zoom+0.0005,1.0565)':d=113,trim=duration=4.5,scale=792:612,setsar=1:1,setpts=PTS-STARTPTS[1vbz];^
#[1vc]zoompan=z=1.0565:d=1,trim=duration=0.5,scale=792:612,setsar=1:1,setpts=PTS-STARTPTS[1vcz];^
#[2va]trim=duration=0.5,scale=792:612,setsar=1:1,setpts=PTS-STARTPTS[2vaz];^
#[2vb]zoompan=z='min(zoom+0.0005,1.0565)':d=113,trim=duration=4.5,scale=792:612,setsar=1:1,setpts=PTS-STARTPTS[2vbz];^
#[2vc]zoompan=z=1.0565:d=1,trim=duration=0.5,scale=792:612,setsar=1:1,setpts=PTS-STARTPTS[2vcz];^
#[0vcz][1vaz]overlay=x='min(-w+(t*w/0.5)\,0)':shortest=1[t1];^
#[1vcz][2vaz]overlay=x='min(-w+(t*w/0.5)\,0)':shortest=1[t2];^
#[0vaz][0vbz][t1][1vbz][t2][2vbz][2vcz]concat=n=7:v=1:a=0[video]" -map [video] -c:v libx264 -pix_fmt yuvj420p -q:v 1 c:\temp/video.mp4
