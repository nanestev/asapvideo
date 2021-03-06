from enum import IntEnum
from core import Filter, FilterExpressionAccessor, Combinable

"""
    Panzoom types
"""
class ZoompanType(IntEnum):
    zoom_in = (1 << 1),
    zoom_out = (1 << 2),
    alternate = (zoom_in[0] | zoom_out[0]),
    random = (alternate[0] | 1 << 0)

class ZoompanEffectFilter(Filter, Combinable):
    def __init__(self, maxzoom, frames, type = ZoompanType.alternate, outstreamprefix="pzf"):
        expressions = []
        step = (maxzoom - 1.0) / frames
        if isinstance(type, ZoompanType) == False:
            type = ZoompanType.alternate
        if type & ZoompanType.zoom_in == ZoompanType.zoom_in:
            expressions.append("zoompan=z='min(zoom+{s},{mz})':d={df}".format(df = frames, s = step, mz = maxzoom))
        if type & ZoompanType.zoom_out == ZoompanType.zoom_out:
            expressions.append("zoompan=z='if(lte(zoom,1.0),{mz},max(1.001,zoom-{s}))':d={df}".format(df = frames, s = step, mz = maxzoom))

        Filter.__init__(self, outstreamprefix)
        Combinable.__init__(self, FilterExpressionAccessor(expressions, type == ZoompanType.random))

    def generate(self, streams):
        return self._generate_base(streams, self.get_accessor())