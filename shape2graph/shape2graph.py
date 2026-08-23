"""Main module."""

import ipyleaflet


class Map(ipyleaflet.Map):
    """A map class that extends ipyleaflet.Map."""

    def __init__(self, center=[20, 0], zoom=2, height="600px", **kwargs):
        super().__init__(center=center, zoom=zoom, **kwargs)
        self.layout.height = height

    def add_basemap(self, basemap="OpenTopoMap"):
        """Add a basemap to the map."""
        basemap_url = eval(f"ipyleaflet.basemaps.{basemap}").build_url()
        tile_layer = ipyleaflet.TileLayer(url=basemap_url, name=basemap)
        self.add_layer(tile_layer)

    def add_google_maps_basemap(self, map_type="roadmap"):
        """Add a Google Maps basemap to the map."""
        map_types = {"roadmap": "m", "satellite": "s", "terrain": "p", "hybrid": "y"}
        google_maps_url = f"https://mt1.google.com/vt/lyrs={map_types.get(map_type, 'm')}&x={{x}}&y={{y}}&z={{z}}"
        tile_layer = ipyleaflet.TileLayer(
            url=google_maps_url, name=f"Google Maps ({map_type})"
        )
        self.add_layer(tile_layer)
