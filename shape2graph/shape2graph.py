"""Main module."""

from click import style
import ipyleaflet
from shapely import bounds
from ipywidgets import widgets


class Map(ipyleaflet.Map):
    """Interactive map with helpers for adding common geospatial data sources.

    The class extends :class:`ipyleaflet.Map` and adds convenience methods for
    basemap tiles and vector data. Vector data is converted to EPSG:4326 before
    it is displayed so that map bounds and centers use latitude/longitude
    coordinates.
    """

    def __init__(
        self, center=[27, 84], zoom=7, height="600px", scroll_wheel_zoom=True, **kwargs
    ):
        """Create an interactive map.

        Args:
            center (list, optional): Initial map center as ``[latitude, longitude]``.
                Defaults to ``[27, 84]``.
            zoom (int, optional): Initial zoom level. Defaults to ``7``.
            height (str, optional): CSS height assigned to the map widget.
                Defaults to ``"600px"``.
            scroll_wheel_zoom (bool, optional): Whether to zoom with the mouse
                wheel. Defaults to ``True``.
            **kwargs: Additional keyword arguments passed to
                :class:`ipyleaflet.Map`.
        """
        super().__init__(
            center=center, zoom=zoom, scroll_wheel_zoom=scroll_wheel_zoom, **kwargs
        )
        self.layout.height = height

    def add_basemap(self, basemap="OpenTopoMap"):
        """Add an ipyleaflet basemap layer to the map.

        Args:
            basemap (str, optional): Name of a basemap available from
                ``ipyleaflet.basemaps``. Defaults to ``"OpenTopoMap"``.
        """
        basemap_url = eval(f"ipyleaflet.basemaps.{basemap}").build_url()
        tile_layer = ipyleaflet.TileLayer(url=basemap_url, name=basemap)
        self.add_layer(tile_layer)

    def add_basemap_gui(self, position="topright"):
        """Add an interactive basemap selector to the map.

        The control contains a toggle to show or hide the basemap selector, a
        dropdown with the supported basemaps, and a button to close the
        control.

        Args:
            position (str, optional): Position of the control on the map.
                Defaults to ``"topright"``.

        Returns:
            None: This method adds the control to the map in place.
        """
        toggle = widgets.ToggleButton(
            value=True,
            button_style="",  # 'success', 'info', 'warning', 'danger' or ''
            tooltip="Click me",
            icon="map",
        )
        toggle.layout = widgets.Layout(width="38px", height="38px")

        dropdown = widgets.Dropdown(
            options=[
                "OpenStreetMap.Mapnik",
                "OpenTopoMap",
                "Esri.WorldImagery",
                "CartoDB.DarkMatter",
            ],
            value="OpenStreetMap.Mapnik",
            description="Basemap:",
            style={"description_width": "initial"},
        )
        dropdown.layout = widgets.Layout(width="250px", height="38px")

        button = widgets.Button(
            icon="times",
        )
        button.layout = widgets.Layout(width="38px", height="38px")

        hbox = widgets.HBox([toggle, dropdown, button])

        def on_toggle_change(change):
            """_summary_

            Args:
                change (_type_): _description_
            """
            if change["new"]:
                hbox.children = [toggle, dropdown, button]
            else:
                hbox.children = [toggle]

        toggle.observe(on_toggle_change, names="value")

        def on_button_click(b):
            hbox.close()
            toggle.close()
            dropdown.close()
            button.close()

        button.on_click(on_button_click)

        def on_dropdown_change(change):
            if change["new"]:
                self.add_basemap(change["new"])

        dropdown.observe(on_dropdown_change, names="value")
        control = ipyleaflet.WidgetControl(widget=hbox, position=position)
        self.add(control)

    def add_widget(self, widget, position="topright"):
        """Add a widget to the map.

        Args:
            widget (ipywidgets.Widget): Widget to add.
            position (str, optional): Position of the widget on the map.
                Defaults to ``"topright"``.
        """
        control = ipyleaflet.WidgetControl(widget=widget, position=position)
        self.add(control)

    def add_google_maps_basemap(self, map_type="roadmap"):
        """Add Google Maps tiles as a basemap layer.

        Args:
            map_type (str, optional): Google Maps tile type. Supported values
                are ``"roadmap"``, ``"satellite"``, ``"terrain"``, and
                ``"hybrid"``. Unknown values use roadmap tiles. Defaults to
                ``"roadmap"``.
        """
        map_types = {"roadmap": "m", "satellite": "s", "terrain": "p", "hybrid": "y"}
        google_maps_url = f"https://mt1.google.com/vt/lyrs={map_types.get(map_type, 'm')}&x={{x}}&y={{y}}&z={{z}}"
        tile_layer = ipyleaflet.TileLayer(
            url=google_maps_url, name=f"Google Maps ({map_type})"
        )
        self.add_layer(tile_layer)

    def add_gdf(self, gdf, zoom_to_layer=True, hover_style=None, **kwargs):
        """Add a GeoDataFrame to the map as a GeoJSON layer.

        The GeoDataFrame is assigned EPSG:4326 when it has no CRS, or
        reprojected to EPSG:4326 when it uses another CRS. By default, the map
        is centered on the layer and fitted to its bounds.

        Args:
            gdf (geopandas.GeoDataFrame): GeoDataFrame to display.
            zoom_to_layer (bool, optional): Whether to center and fit the map
                to the layer bounds. Defaults to ``True``.
            hover_style (dict, optional): Leaflet style applied while hovering
                over a feature. Defaults to a white fill with a red outline.
            **kwargs: Additional keyword arguments passed to
                :class:`ipyleaflet.GeoJSON`.
        """

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
        """Load GeoJSON data and add it to the map.

        Args:
            data (str or dict): Path to a GeoJSON file, or a GeoJSON
                dictionary.
            **kwargs: Additional keyword arguments passed to :meth:`add_gdf`.

        Raises:
            TypeError: If ``data`` is neither a file path string nor a
                GeoJSON dictionary.
        """
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
        """Load a shapefile and add it to the map.

        Args:
            shapefile_path (str): Path to the shapefile.
            **kwargs: Additional keyword arguments passed to :meth:`add_gdf`.

        Raises:
            TypeError: If ``shapefile_path`` is not a file path string.
        """

        import geopandas as gpd

        if isinstance(shapefile_path, str):
            gdf = gpd.read_file(shapefile_path)
        else:
            raise TypeError("shapefile_path must be a file path string")

        self.add_gdf(gdf, **kwargs)

    def add_vector(self, data, **kwargs):
        """Load vector data and add it to the map.

        GeoDataFrames and GeoJSON dictionaries are accepted directly. Strings
        may contain a local path, URL, directory, or raw GeoJSON object. The
        loaded data is passed to :meth:`add_gdf` for display.

        Args:
            data (geopandas.GeoDataFrame, dict, or str): Vector data as a
                GeoDataFrame, GeoJSON dictionary, local path, URL, directory,
                or raw JSON string.
            **kwargs: Additional keyword arguments passed to :meth:`add_gdf`.

        Raises:
            ValueError: If a string source cannot be loaded.
            TypeError: If ``data`` has an unsupported type.

        Returns:
            None: This method adds a layer to the map in place.
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

    def add_splitmap(
        self,
        left_layer="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        right_layer="https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
        **kwargs,
    ):
        """Add a split map with two layers.

        Args:
            left_layer (ipyleaflet.Layer): Layer to display on the left side.
            right_layer (ipyleaflet.Layer): Layer to display on the right side.
            **kwargs: Additional keyword arguments passed to
                :class:`ipyleaflet.SplitMapControl`.
        """

        from ipyleaflet import Map, TileLayer, SplitMapControl

        # Define the left and right tile layers
        left_layer = TileLayer(url=left_layer)
        right_layer = TileLayer(url=right_layer)

        # Create the split control and add it to the map
        split_control = ipyleaflet.SplitMapControl(
            left_layer=left_layer, right_layer=right_layer, **kwargs
        )
        self.add_control(split_control)

    def add_raster(self, raster_path, **kwargs):
        """Load a raster file and add it to the map."""
        from localtileserver import TileClient, get_leaflet_tile_layer

        client = TileClient(raster_path)
        tile_layer = get_leaflet_tile_layer(client, **kwargs)
        self.add(tile_layer)
        self.center = client.center()
        self.zoom = client.default_zoom

    def add_image(self, image, bounds=None, **kwargs):
        """Add an image to the map.

        Args:
            image (str or array-like): Path to an image file or a NumPy array.
            bounds (list, optional): Bounds of the image as
                ``[[south, west], [north, east]]``. If not provided, the image
                is assumed to cover the entire world.
            **kwargs: Additional keyword arguments passed to
                :class:`ipyleaflet.ImageOverlay`.
        """
        if bounds is None:
            bounds = ((-90, -180), (90, 180))
        image_overlay = ipyleaflet.ImageOverlay(url=image, bounds=bounds, **kwargs)
        self.add(image_overlay)

    def add_video(self, video, bounds=None, **kwargs):
        """Add a video to the map.

        Args:
            video (str): Path to a video file.
            bounds (list, optional): Bounds of the video as
                ``[[south, west], [north, east]]``. If not provided, the video
                is assumed to cover the entire world.
            **kwargs: Additional keyword arguments passed to
                :class:`ipyleaflet.VideoOverlay`.
        """
        if bounds is None:
            bounds = ((-90, -180), (90, 180))
        video_overlay = ipyleaflet.VideoOverlay(url=video, bounds=bounds, **kwargs)
        self.add(video_overlay)

    def add_wms_layer(
        self,
        url,
        layers,
        format="image/png",
        transparent=True,
        attribution="",
        **kwargs,
    ):
        """Add a WMS layer to the map.

        Args:
            url (str): URL of the WMS service.
            layers (str): Comma-separated list of layer names to display.
            format (str, optional): Image format for the WMS layer. Defaults to "image/png".
            transparent (bool, optional): Whether the WMS layer should be transparent. Defaults to True.
            attribution (str, optional): Attribution text for the WMS layer. Defaults to an empty string.
            **kwargs: Additional keyword arguments passed to :class:`ipyleaflet.WMSLayer`.
        """
        wms_layer = ipyleaflet.WMSLayer(
            url=url,
            layers=layers,
            format=format,
            transparent=transparent,
            attribution=attribution,
            **kwargs,
        )
        self.add(wms_layer)
