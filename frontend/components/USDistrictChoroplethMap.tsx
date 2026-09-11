'use client';

import { useEffect, useMemo, useState } from 'react';

export interface CODistrictData {
  district: string;
  district_number: string;
  representative: string;
  party?: 'R' | 'D';
  region: string;
  average_household_income_change: number;
  relative_household_income_change: number;
  winners_share?: number;
  losers_share?: number;
  poverty_pct_change?: number;
  child_poverty_pct_change?: number;
  state?: string;
}

interface Props {
  data: CODistrictData[];
  selectedDistrict: string | null;
  onSelect: (districtNumber: string) => void;
}

// PolicyEngine diverging scale (gray -> teal): most negative impact
// renders gray, most positive renders teal.
const DIVERGING_COLORS = [
  '#475569', // gray-600 (most negative)
  '#94A3B8', // gray-400
  '#E2E8F0', // gray-200 (neutral / zero)
  '#81E6D9', // teal-200
  '#319795', // teal-500 (most positive)
];

const VB_W = 800;
const VB_H = 620;
const VB_PAD = 16;

const CO_STATE_FIPS = '08';
const GEOJSON_PATH = 'data/geojson/congressional_districts.geojson';

type Ring = [number, number][];
interface GeoFeature {
  type: 'Feature';
  properties: {
    STATEFP?: string;
    CD119FP?: string;
    DISTRICT_ID?: string;
    NAMELSAD?: string;
  };
  geometry:
    | { type: 'Polygon'; coordinates: Ring[] }
    | { type: 'MultiPolygon'; coordinates: Ring[][] };
}
interface GeoCollection {
  type: 'FeatureCollection';
  features: GeoFeature[];
}
interface DistrictGeometry {
  districtNumber: string;
  path: string;
  cx: number;
  cy: number;
}

function interpolateColor(value: number, min: number, max: number): string {
  if (min >= max) return DIVERGING_COLORS[2];
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const segments = DIVERGING_COLORS.length - 1;
  const segPos = t * segments;
  const segIndex = Math.min(Math.floor(segPos), segments - 1);
  const segT = segPos - segIndex;
  const parse = (hex: string) => [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
  const c0 = parse(DIVERGING_COLORS[segIndex]);
  const c1 = parse(DIVERGING_COLORS[segIndex + 1]);
  const mix = (a: number, b: number) => Math.round(a + (b - a) * segT);
  return `rgb(${mix(c0[0], c1[0])}, ${mix(c0[1], c1[1])}, ${mix(c0[2], c1[2])})`;
}

const formatCurrency = (value: number) => {
  if (Math.abs(value) >= 1000) return `$${(value / 1000).toFixed(1)}k`;
  return `$${value.toFixed(0)}`;
};
const formatSignedCurrency = (value: number) => {
  const base = formatCurrency(Math.abs(value));
  if (value > 0) return `+${base}`;
  if (value < 0) return `-${base}`;
  return base;
};

function iterateRings(geom: GeoFeature['geometry']): Ring[] {
  if (geom.type === 'Polygon') return geom.coordinates;
  return geom.coordinates.flat();
}

function computeBBox(features: GeoFeature[]) {
  let minLon = Infinity;
  let maxLon = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;
  for (const f of features) {
    for (const ring of iterateRings(f.geometry)) {
      for (const [lon, lat] of ring) {
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
      }
    }
  }
  return { minLon, maxLon, minLat, maxLat };
}

function makeProjector(bbox: ReturnType<typeof computeBBox>) {
  const meanLat = (bbox.minLat + bbox.maxLat) / 2;
  const lonScale = Math.cos((meanLat * Math.PI) / 180);
  const geoW = (bbox.maxLon - bbox.minLon) * lonScale;
  const geoH = bbox.maxLat - bbox.minLat;
  const availW = VB_W - 2 * VB_PAD;
  const availH = VB_H - 2 * VB_PAD;
  const scale = Math.min(availW / geoW, availH / geoH);
  const drawnW = geoW * scale;
  const drawnH = geoH * scale;
  const offsetX = VB_PAD + (availW - drawnW) / 2;
  const offsetY = VB_PAD + (availH - drawnH) / 2;
  return (lon: number, lat: number): [number, number] => {
    const x = offsetX + (lon - bbox.minLon) * lonScale * scale;
    const y = offsetY + (bbox.maxLat - lat) * scale;
    return [x, y];
  };
}

function ringToPath(ring: Ring, project: (lon: number, lat: number) => [number, number]): string {
  const out: string[] = [];
  for (let i = 0; i < ring.length; i++) {
    const [lon, lat] = ring[i];
    const [x, y] = project(lon, lat);
    out.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`);
  }
  out.push('Z');
  return out.join(' ');
}

function featureToPath(
  feature: GeoFeature,
  project: (lon: number, lat: number) => [number, number],
) {
  const rings = iterateRings(feature.geometry);
  const path = rings.map((r) => ringToPath(r, project)).join(' ');
  let sx = 0;
  let sy = 0;
  let n = 0;
  for (const ring of rings) {
    for (const [lon, lat] of ring) {
      const [x, y] = project(lon, lat);
      sx += x;
      sy += y;
      n += 1;
    }
  }
  return {
    path,
    cx: n > 0 ? sx / n : VB_W / 2,
    cy: n > 0 ? sy / n : VB_H / 2,
  };
}

/** Extract the district number ("1".."8") from a feature's properties,
 *  supporting both the DISTRICT_ID ("CO-01") and CD119FP ("01") keys. */
function getDistrictNumber(props: GeoFeature['properties']): string | null {
  if (props.DISTRICT_ID) {
    const part = props.DISTRICT_ID.split('-')[1];
    if (part) return String(parseInt(part, 10));
  }
  if (props.CD119FP) {
    const num = parseInt(props.CD119FP, 10);
    if (!Number.isNaN(num)) return String(num);
  }
  return null;
}

export default function CODistrictChoroplethMap({
  data,
  selectedDistrict,
  onSelect,
}: Props) {
  const [geometries, setGeometries] = useState<DistrictGeometry[] | null>(null);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    districtNumber: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const basePath =
          process.env.NEXT_PUBLIC_BASE_PATH !== undefined
            ? process.env.NEXT_PUBLIC_BASE_PATH
            : '/us/co-initiative-195';
        const res = await fetch(`${basePath}/${GEOJSON_PATH}`);
        if (!res.ok) throw new Error(`Failed to load geojson (${res.status})`);
        const json = (await res.json()) as GeoCollection;
        // The geojson may be national or Colorado-only; filter to CO
        // either way.
        const coFeatures = json.features.filter(
          (f) =>
            f.properties.STATEFP === CO_STATE_FIPS ||
            (f.properties.DISTRICT_ID ?? '').startsWith('CO-'),
        );
        if (coFeatures.length === 0) {
          throw new Error('No Colorado features in the geojson');
        }
        const bbox = computeBBox(coFeatures);
        const project = makeProjector(bbox);
        const geom: DistrictGeometry[] = [];
        for (const f of coFeatures) {
          const districtNumber = getDistrictNumber(f.properties);
          if (!districtNumber) continue;
          const { path, cx, cy } = featureToPath(f, project);
          geom.push({ districtNumber, path, cx, cy });
        }
        geom.sort(
          (a, b) => Number(a.districtNumber) - Number(b.districtNumber),
        );
        if (!cancelled) setGeometries(geom);
      } catch (e) {
        if (!cancelled) {
          setGeoError(e instanceof Error ? e.message : String(e));
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const dataByDistrict = useMemo(() => {
    const map = new Map<string, CODistrictData>();
    data.forEach((d) =>
      map.set(String(parseInt(d.district_number, 10)), d),
    );
    return map;
  }, [data]);

  // Symmetric color range so zero always maps to the neutral midpoint.
  const colorRange = useMemo(() => {
    if (data.length === 0) return { min: 0, max: 0 };
    const values = data.map((d) => d.average_household_income_change);
    const maxAbs = Math.max(...values.map(Math.abs));
    return { min: -maxAbs, max: maxAbs };
  }, [data]);

  const tooltipData = tooltip
    ? dataByDistrict.get(tooltip.districtNumber)
    : null;

  return (
    <div className="relative">
      {geoError && (
        <div className="mb-3 rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
          Could not load the Colorado geography ({geoError}).
        </div>
      )}
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        style={{ width: '100%', height: 'auto', maxHeight: 560 }}
        role="img"
        aria-label="Choropleth of Colorado's 8 congressional districts"
      >
        {geometries &&
          geometries.map((g) => {
            const districtData = dataByDistrict.get(g.districtNumber);
            const value = districtData?.average_household_income_change ?? 0;
            const fill = districtData
              ? interpolateColor(value, colorRange.min, colorRange.max)
              : '#E2E8F0';
            const isSelected = selectedDistrict === g.districtNumber;

            return (
              <g
                key={g.districtNumber}
                style={{ cursor: 'pointer' }}
                onClick={() => onSelect(g.districtNumber)}
                onMouseEnter={(evt) =>
                  setTooltip({
                    x: evt.clientX,
                    y: evt.clientY,
                    districtNumber: g.districtNumber,
                  })
                }
                onMouseMove={(evt) =>
                  setTooltip({
                    x: evt.clientX,
                    y: evt.clientY,
                    districtNumber: g.districtNumber,
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              >
                <path
                  d={g.path}
                  fill={fill}
                  stroke={isSelected ? '#0f766e' : '#ffffff'}
                  strokeWidth={isSelected ? 2.5 : 1}
                  strokeLinejoin="round"
                  style={{
                    transition: 'opacity 0.15s',
                    opacity:
                      tooltip && tooltip.districtNumber !== g.districtNumber
                        ? 0.7
                        : 1,
                  }}
                />
                <text
                  x={g.cx}
                  y={g.cy}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="16"
                  fontWeight="700"
                  fill="#ffffff"
                  stroke="#334155"
                  strokeWidth="0.4"
                  paintOrder="stroke"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {g.districtNumber}
                </text>
              </g>
            );
          })}
      </svg>

      {tooltip && tooltipData && (
        <div
          className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 pointer-events-none"
          style={{ left: tooltip.x + 10, top: tooltip.y + 10 }}
        >
          <p className="font-semibold text-gray-900">
            CO-{String(tooltipData.district_number).padStart(2, '0')}
          </p>
          {tooltipData.representative && (
            <p className="text-sm text-gray-700">{tooltipData.representative}</p>
          )}
          <p className="text-sm text-gray-600">
            Avg impact:{' '}
            {formatSignedCurrency(tooltipData.average_household_income_change)}
          </p>
          <p className="text-sm text-gray-600">
            ({(tooltipData.relative_household_income_change * 100).toFixed(2)}%
            of income)
          </p>
        </div>
      )}

      <p className="text-xs text-gray-500 text-center mt-4">
        Estimated average household net-income change under the Initiative 195
        graduated schedule vs. current law, by Colorado congressional district
        (119th Congress)
      </p>
    </div>
  );
}
