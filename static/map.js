window.addEventListener("load", function () {
  const ROUTE_TYPE = window.location.href.split("/").slice(-2)[0].toUpperCase();
  setFavicon(window.location.href, ROUTE_TYPE);
  setImages(window.location.href, ROUTE_TYPE);
  setDescriptions(ROUTE_TYPE);
  setTitles(ROUTE_TYPE);
  setUrls();
  setNavbar("navbar", ROUTE_TYPE, window.mobileCheck());
  createMap("map", ROUTE_TYPE);
});
/** map factory function for map.html
 * @param {string} id - id of the map div
 * @param {string} route_type - route type
 * @returns {L.map} map
 */
function createMap(id, route_type) {
  const map = L.map(id, {
    minZoom: 9,
    maxZoom: 20,
    maxBounds: L.latLngBounds(L.latLng(40, -74), L.latLng(44, -69)),
    fullscreenControl: true,
    fullscreenControlOptions: {
      position: "topleft",
    },
    attributionControl: true,
  }).setView([42.3519, -71.0552], route_type == "COMMUTER_RAIL" ? 10 : 13);

  const baseLayers = getBaseLayerDict(...Array(2), {
    Alt: "Stadia.AlidadeSmoothDark",
  });
  baseLayers["Light"].addTo(map);

  let stop_layer = L.layerGroup().addTo(map);
  stop_layer.name = "Stops";

  let shape_layer = L.layerGroup().addTo(map);
  shape_layer.name = "Shapes";

  let vehicle_layer = L.markerClusterGroup({
    disableClusteringAtZoom: route_type == "COMMUTER_RAIL" ? 10 : 12,
  }).addTo(map);
  vehicle_layer.name = "Vehicles";

  let parking_lots = L.layerGroup();
  parking_lots.name = "Parking Lots";

  plotStops(`/static/geojsons/${route_type}/stops.json`, stop_layer);
  plotShapes(`/static/geojsons/${route_type}/shapes.json`, shape_layer);
  plotVehicles(`/${route_type.toLowerCase()}/vehicles`, vehicle_layer);
  plotFacilities(`/static/geojsons/${route_type}/park.json`, parking_lots);

  createControlLayers(
    baseLayers,
    stop_layer,
    shape_layer,
    vehicle_layer,
    parking_lots
  ).forEach((control) => control.addTo(map));

  map.on("zoomend", function () {
    if (map.getZoom() < 16) map.removeLayer(parking_lots);
    if (map.getZoom() >= 16) map.addLayer(parking_lots);
  });

  if (map.hasLayer(parking_lots)) map.removeLayer(parking_lots);

  return map;
}
/** create control layers
 * @param {Object} tile_layers - base layers
 * @param {L.layerGroup} layers - layers to be added to the map
 * @returns {Array} control layers
 */
function createControlLayers(tile_layers, ...layers) {
  const locateControl = L.control.locate({
    enableHighAccuracy: true,
    initialZoomLevel: 15,
    metric: false,
    markerStyle: {
      zIndexOffset: 500,
    },
  });

  const controlSearch = L.control.search({
    layer: L.layerGroup(layers),
    initial: false,
    propertyName: "name",
    zoom: 16,
    marker: false,
    textPlaceholder: "",
  });
  controlSearch.on("search:locationfound", function (event) {
    event.layer.openPopup();
  });

  const layerControl = L.control.layers(
    tile_layers,
    Object.fromEntries(layers.map((layer) => [layer.name, layer]))
  );

  return [locateControl, controlSearch, layerControl];
}
