import geopandas as gpd
from shapely.ops import unary_union, linemerge
from shapely.geometry import Point
import networkx as nx
import momepy
import shape2graph
import ipyleaflet
import ipywidgets as widgets


def visualize_map(
    gdf, basemap="OpenStreetMap.Mapnik", center=[27.7, 85.3], zoom=12, style=None
):
    """
    Visualizes a GeoDataFrame on an interactive shape2graph map.
    """
    m = shape2graph.Map(center=center, zoom=zoom)
    m.add_basemap(basemap)
    if style is None:
        style = {"color": "blue", "weight": 2, "opacity": 1.0}
    m.add_gdf(gdf, zoom_to_layer=True, style=style)
    return m


def correct_topology(vector_url):
    """
    Takes a vector url/path, loads the shapefile, reprojects, drops duplicates,
    planarizes, heals pseudo-nodes, and trims micro-dangles.
    """
    print("Loading shapefile...")
    gdf = gpd.read_file(vector_url)

    # Ensure EPSG:32645 projected CRS
    if gdf.crs and gdf.crs != "EPSG:32645":
        gdf = gdf.to_crs("EPSG:32645")
    elif not gdf.crs:
        gdf = gdf.set_crs("EPSG:32645")

    # Drop duplicates
    initial_count = len(gdf)
    gdf = gdf.drop_duplicates(subset=["geometry"])
    print(f"Removed {initial_count - len(gdf)} duplicate overlapping lines.")

    # Planarize network
    print("Planarizing the network...")
    merged_lines = unary_union(gdf.geometry)
    if merged_lines.geom_type == "MultiLineString":
        segments = list(merged_lines.geoms)
    else:
        segments = [merged_lines]
    planar_gdf = gpd.GeoDataFrame(geometry=segments, crs=gdf.crs)

    # Heal pseudo-nodes
    print("Healing pseudo-nodes...")
    healed_lines = linemerge(planar_gdf.geometry.tolist())
    if healed_lines.geom_type == "MultiLineString":
        healed_segments = list(healed_lines.geoms)
    else:
        healed_segments = [healed_lines]
    healed_gdf = gpd.GeoDataFrame(geometry=healed_segments, crs=planar_gdf.crs)

    # Trim micro-dangles
    print("Trimming micro-dangles...")
    healed_gdf["length"] = healed_gdf.geometry.length
    tolerance = 2.0
    clean_gdf = healed_gdf[healed_gdf["length"] > tolerance].copy()
    print(f"Final cleaned segments ready for NetworkX: {len(clean_gdf)}")

    return clean_gdf


def run_shortest_path(clean_gdf, start_node, end_node):
    """
    Converts the cleaned GeoDataFrame to a NetworkX graph, calculates the shortest path
    between start_node and end_node (coordinate tuples), and visualizes the result on a map.
    """
    print("Converting GeoDataFrame to NetworkX graph...")
    G = momepy.gdf_to_nx(clean_gdf, approach="primal")

    # Extract largest connected component
    components = list(nx.connected_components(G))
    largest_cc = max(components, key=len)
    G_main = G.subgraph(largest_cc).copy()

    # Assign edge weights
    for u, v, data in G_main.edges(data=True):
        if "length" not in data:
            data["weight"] = data["geometry"].length if "geometry" in data else 1.0
        else:
            data["weight"] = data["length"]

    # Calculate shortest path
    try:
        shortest_path = nx.shortest_path(
            G_main, source=start_node, target=end_node, weight="weight"
        )
        print(f"Successfully calculated a path containing {len(shortest_path)} nodes!")
    except nx.NetworkXNoPath:
        print("No valid path found between the specified nodes.")
        return None, None

    # Extract path geometries
    path_geometries = []
    for i in range(len(shortest_path) - 1):
        u, v = shortest_path[i], shortest_path[i + 1]
        edge_data = G_main.get_edge_data(u, v)
        if isinstance(edge_data, dict) and len(edge_data) > 0:
            first_key = list(edge_data.keys())[0]
            geom = edge_data[first_key].get("geometry")
        else:
            geom = edge_data.get("geometry")
        if geom:
            path_geometries.append(geom)

    path_gdf = gpd.GeoDataFrame(geometry=path_geometries, crs=clean_gdf.crs)
    _, edges_gdf = momepy.nx_to_gdf(G_main, points=True, lines=True)
    edges_gdf = edges_gdf.set_crs(clean_gdf.crs)

    # Visualize map
    m = shape2graph.Map(center=[27.7, 85.3], zoom=12)
    m.add_basemap("CartoDB.DarkMatter")
    m.add_gdf(
        edges_gdf,
        zoom_to_layer=False,
        style={"color": "white", "weight": 1, "opacity": 0.3},
        name="Full Network",
    )
    m.add_gdf(
        path_gdf,
        zoom_to_layer=True,
        style={"color": "#00FF00", "weight": 5, "opacity": 1.0},
        name="Shortest Path",
    )

    return m, path_gdf


def create_interactive_router(clean_gdf):
    """
    Launches an interactive ipyleaflet widget allowing users to click start and end
    points on the map, automatically resolving coordinate tuples and rendering routes.
    """
    G = momepy.gdf_to_nx(clean_gdf, approach="primal")
    G_main = G.subgraph(max(nx.connected_components(G), key=len)).copy()

    nodes_gdf, edges_gdf = momepy.nx_to_gdf(G_main, points=True, lines=True)
    nodes_gdf["node_key"] = list(G_main.nodes())
    nodes_gdf = nodes_gdf.set_crs(clean_gdf.crs)
    edges_gdf = edges_gdf.set_crs(clean_gdf.crs)

    m = shape2graph.Map(center=[27.7, 85.3], zoom=12)
    m.add_basemap("OpenStreetMap.Mapnik")
    m.add_gdf(
        edges_gdf,
        style={"color": "blue", "weight": 2, "opacity": 1},
        name="Full Network",
    )

    markers_layer = ipyleaflet.LayerGroup()
    path_layer = ipyleaflet.LayerGroup()
    m.add(markers_layer)
    m.add(path_layer)

    start_node = None
    end_node = None

    def find_nearest_node(lat, lon):
        click_gdf = gpd.GeoDataFrame(
            geometry=[Point(lon, lat)], crs="EPSG:4326"
        ).to_crs("EPSG:32645")
        p = click_gdf.geometry.iloc[0]
        distances = nodes_gdf.geometry.distance(p)
        closest_idx = distances.idxmin()
        return (
            nodes_gdf.loc[closest_idx, "node_key"],
            nodes_gdf.loc[closest_idx, "geometry"],
        )

    def handle_map_click(**kwargs):
        nonlocal start_node, end_node
        if kwargs.get("type") == "click":
            lat, lon = kwargs.get("coordinates")
            node_key, geom_32645 = find_nearest_node(lat, lon)
            p_4326 = (
                gpd.GeoSeries([geom_32645], crs="EPSG:32645")
                .to_crs("EPSG:4326")
                .iloc[0]
            )

            if start_node is None:
                start_node = node_key
                markers_layer.add(
                    ipyleaflet.Marker(
                        location=(p_4326.y, p_4326.x),
                        draggable=False,
                        title="Start Node",
                    )
                )
                print(f"Start node set: {start_node}")
            elif end_node is None:
                end_node = node_key
                markers_layer.add(
                    ipyleaflet.Marker(
                        location=(p_4326.y, p_4326.x), draggable=False, title="End Node"
                    )
                )
                print(f"End node set: {end_node}")
            else:
                print("Both points already set. Click 'Clear Display' to reset.")

    m.on_interaction(handle_map_click)

    run_btn = widgets.Button(description="Run Shortest Path", button_style="success")
    clear_btn = widgets.Button(description="Clear Display", button_style="danger")

    def on_run_clicked(b):
        nonlocal start_node, end_node
        if start_node is not None and end_node is not None:
            path_map, path_gdf = run_shortest_path(clean_gdf, start_node, end_node)
            if path_gdf is not None:
                path_layer.clear_layers()
                path_gdf_4326 = path_gdf.to_crs("EPSG:4326")
                path_geojson = ipyleaflet.GeoJSON(
                    data=path_gdf_4326.__geo_interface__,
                    style={"color": "#00FF00", "weight": 6, "opacity": 1.0},
                )
                path_layer.add(path_geojson)
                print("Path successfully rendered on interactive map!")
        else:
            print("Please click two points on the map first.")

    def on_clear_clicked(b):
        nonlocal start_node, end_node
        start_node, end_node = None, None
        markers_layer.clear_layers()
        path_layer.clear_layers()
        print("Map cleared. Select new start and end points.")

    run_btn.on_click(on_run_clicked)
    clear_btn.on_click(on_clear_clicked)

    return widgets.VBox([widgets.HBox([run_btn, clear_btn]), m])
