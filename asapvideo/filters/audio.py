from core import Filter, FilterExpressionAccessor

"""
    Replicate audio filter
"""
class ReplicateAudioFilter(Filter):
    def __init__(self, repetitions, outstreamprefix="raf"):
        super(self.__class__, self).__init__(outstreamprefix)
        self._repetitions = repetitions

    def generate(self, streams):
        output = []
        newstreams = []
        i = 0
        for s in streams:
            for _ in range(0,self._repetitions):
                ns = self._outstreamprefix
                if i > 0: ns += str(i)
                newstreams.append(ns)
                output.append("[{s}]afifo[{ns}]".format(s=s, ns=ns))
                i += 1
        return output, newstreams

"""
    Trim audio filter
"""
class TrimAudioFilter(Filter):
    def __init__(self, length, outstreamprefix="atf"):
        super(self.__class__, self).__init__(outstreamprefix)
        self._expressions_accessor = FilterExpressionAccessor([
            "aselect=between(t\,0\,%d)" % length
        ])

    def generate(self, streams):
        return self._generate_base(streams, self._expressions_accessor)

"""
    Fade out audio filter
"""
class FadeOutAudioFilter(Filter):
    def __init__(self, start, length, outstreamprefix="afof"):
        super(self.__class__, self).__init__(outstreamprefix)
        self._expressions_accessor = FilterExpressionAccessor([
            "volume='if(lt(t,%d),1,max(1-(t-%d)/%d,0))':eval=frame" % (start,start,length)
        ])

    def generate(self, streams):
        return self._generate_base(streams, self._expressions_accessor)