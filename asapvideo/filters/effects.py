from core import Filter, FilterExpressionsAccessor

class PanZoomEffectFilter(Filter):
    def __init__(self, frames):
        self._expressions_accessor = FilterExpressionsAccessor([
            "zoompan=z='min(zoom+0.0015,1.5)':d={df}".format(df = frames), 
            "zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={df}".format(df = frames)
        ])

    def generate(self, streams):
        return self._generate_base(streams, "pz", self._expressions_accessor)