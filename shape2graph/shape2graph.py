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

    def add_gdf(self, gdf, zoom_to_layer=True, hover_style=None, **kwargs):
        """Add a GeoPandas GeoDataFrame layer to the map."""
        if hover_style is None:
            hover_style = {"fillColor": "white", "color": "red", "fillOpacity": 0.5}

        # 1. FORCE EPSG:4326 (Latitude/Longitude) so bounds are calculated correctly
        if gdf.crs and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        elif not gdf.crs:
            gdf = gdf.set_crs("EPSG:4326")

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

    def add_geojson(self, data, **kwargs):
        """Add a GeoJSON layer to the map."""
        import geopandas as gpd

        # Handle both file paths (strings) and pre-loaded dictionaries
        if isinstance(data, str):
            gdf = gpd.read_file(data)
        elif isinstance(data, dict):
            gdf = gpd.GeoDataFrame.from_features(data, crs="EPSG:4326")
        else:
            raise TypeError("data must be a file path string or a GeoJSON dictionary")

        self.add_gdf(gdf, **kwargs)

    def add_shapefile(self, shapefile_path, **kwargs):
        """Add a shapefile layer to the map."""
        import geopandas as gpd

        if isinstance(shapefile_path, str):
            gdf = gpd.read_file(shapefile_path)
        else:
            raise TypeError("shapefile_path must be a file path string")

        self.add_gdf(gdf, **kwargs)

    def add_vector(self, data, **kwargs):
        """
        Add any vector data to the map.
        Supports local file paths, directories, URLs, GeoJSON dictionaries, and GeoDataFrames.
        """
        import geopandas as gpd
        import json

        # 1. If it's already a GeoDataFrame
        if isinstance(data, gpd.GeoDataFrame):
            gdf = data

        # 2. If it's a Dictionary (GeoJSON structure)
        elif isinstance(data, dict):
            # GeoPandas expects the features list, but can also handle the full FeatureCollection dict
            if "features" in data:
                gdf = gpd.GeoDataFrame.from_features(data, crs="EPSG:4326")
            else:
                # Wrap it in a list if it's a single geometry/feature
                gdf = gpd.GeoDataFrame.from_features([data], crs="EPSG:4326")

        # 3. If it's a String (URL, Local Path, Local Directory, or raw JSON string)
        elif isinstance(data, str):
            # Catch raw JSON strings passed directly
            if data.strip().startswith("{") and data.strip().endswith("}"):
                try:
                    parsed_dict = json.loads(data)
                    # Recursively call this function with the parsed dictionary
                    return self.add_vector(parsed_dict, **kwargs)
                except json.JSONDecodeError:
                    pass  # Fall back to read_file if it's not actually JSON

            # read_file inherently handles URLs (http/https), local files, and folders containing shapefiles
            try:
                gdf = gpd.read_file(data)
            except Exception as e:
                raise ValueError(f"Failed to load data from {data}. Error: {e}")

        else:
            raise TypeError(
                "Unsupported data type. Please provide a URL, local path, "
                "GeoJSON dictionary, or GeoDataFrame."
            )

        # Pass the unified GeoDataFrame to the core add_gdf method
        self.add_gdf(gdf, **kwargs)
