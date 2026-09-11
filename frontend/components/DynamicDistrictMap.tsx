'use client';

// The Colorado district visualization renders as a self-contained SVG
// choropleth — no browser-only deps that need lazy loading — so we can
// re-export the component directly. The CODistrictData type is
// re-exported so consumers that import the type from this module
// continue to compile.
export { default } from './USDistrictChoroplethMap';
export type { CODistrictData } from './USDistrictChoroplethMap';
