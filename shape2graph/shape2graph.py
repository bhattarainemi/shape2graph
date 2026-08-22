"""Main module."""

import ipyleaflet


class Map(ipyleaflet.Map):
    """A map class that extends ipyleaflet.Map."""

    def __init__(self, center=[20, 0], zoom=2, height="600px", **kwargs):
        super().__init__(center=center, zoom=zoom, **kwargs)
        self.layout.height = height
