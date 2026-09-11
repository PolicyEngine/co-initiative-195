'use client';

// The Colorado Initiative 195 dashboard uses a single CO-only SVG
// choropleth for the 8 congressional districts; a geographic/hex
// map-type toggle is not meaningful at this scale. This stub is kept
// only to preserve the import path used by legacy callers; it renders
// nothing.

interface Props {
  mapType?: 'geographic' | 'hex';
  onChange?: (type: 'geographic' | 'hex') => void;
}

export default function MapTypeToggle(_props: Props) {
  void _props;
  return null;
}
