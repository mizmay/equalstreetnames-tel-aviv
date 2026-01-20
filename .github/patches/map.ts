'use strict';

import mapboxgl, { Map, MapboxOptions, NavigationControl, ScaleControl } from 'maplibre-gl';
import MapboxGeocoder from '@mapbox/mapbox-gl-geocoder';

import addBoundary from './map/layers/boundary';
import addRelations from './map/layers/relation';
import addWays from './map/layers/ways';
import addEvents from './map/events';

import { lang, center, zoom, bbox, style, bounds } from './index';
import { theme } from './theme';

export let map: Map;

// Store Mapbox token for geocoder (if available)
const mapboxToken = process.env.MAPBOX_TOKEN || '';

export default async function (): Promise<Map> {
  const options: MapboxOptions = {
    container: 'map',
    hash: true,
    style: typeof style !== 'undefined' ? style : 'https://tiles.openfreemap.org/styles/positron'
  };

  if (typeof center !== 'undefined' && typeof zoom !== 'undefined') {
    options.center = center;
    options.zoom = zoom;
  } else {
    options.bounds = bbox || bounds;
    options.fitBoundsOptions = { padding: 50 };
  }

  // Initialize map.
  if (typeof map !== 'undefined') {
    map.remove();
  }
  map = new Map(options);

  // Add controls.
  const nav = new NavigationControl({ showCompass: false });
  map.addControl(nav, 'top-left');

  const scale = new ScaleControl({ unit: 'metric' });
  map.addControl(scale);

  // Only add geocoder if Mapbox access token is available
  if (mapboxToken) {
    const geocoder = new MapboxGeocoder({
      accessToken: mapboxToken,
      bbox: bbox || bounds,
      enableEventLogging: false,
      language: lang,
      mapboxgl: mapboxgl as any // Type assertion needed for MapLibre compatibility
    });
    map.addControl(geocoder as any); // Type assertion needed for MapLibre compatibility
  }

  map.on('load', () => {
    map.resize();

    // Add GeoJSON sources.
    addRelations(map);
    addWays(map);
    addBoundary(map);

    // Add events
    addEvents(map);
  });

  map.on('idle', () => {
    document.body.classList.add('loaded');
  });

  return map;
}
