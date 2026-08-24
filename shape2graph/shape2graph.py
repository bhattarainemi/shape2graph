"""Main module."""

from click import style
import ipyleaflet
from shapely import bounds


class Map(ipyleaflet.Map):
    """A map class that extends ipyleaflet.Map."""

    def __init__(
        self, center=[27, 85], zoom=4, height="600px", scroll_wheel_zoom=True, **kwargs
    ):
        super().__init__(
            center=center, zoom=zoom, scroll_wheel_zoom=scroll_wheel_zoom, **kwargs
        )
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

    def add_geojson(self, data, zoom_to_layer=True, hover_style=None, **kwargs):
        """Add a GeoJSON layer to the map."""
        import geopandas as gpd

        if hover_style is None:
            hover_style = {"fillColor": "white", "color": "red", "fillOpacity": 0.5}

        gdf = gpd.read_file(data)

        # 1. FORCE EPSG:4326 (Latitude/Longitude) so bounds are calculated correctly
        if gdf.crs and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        geojson_dict = gdf.__geo_interface__

        # Pass any extra kwargs (like style) into the GeoJSON layer
        layer = ipyleaflet.GeoJSON(data=geojson_dict, hover_style=hover_style, **kwargs)
        self.add_layer(layer)

        if zoom_to_layer:
            bounds = gdf.total_bounds

            # 2. Set the center manually as a fallback in case the map isn't rendered yet
            self.center = ((bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2)

            # 3. Fit bounds (Note: this only perfectly sizes the zoom if the map is already visible)
            self.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
