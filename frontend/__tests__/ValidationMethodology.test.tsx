import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ValidationMethodology from '../components/ValidationMethodology';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('ValidationMethodology', () => {
  beforeEach(() => {
    // Simulate the pre-Modal-run state: no CSVs present yet.
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 404 })
    ) as typeof fetch;
  });

  it('shows the official LCS estimate', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ValidationMethodology />
      </QueryClientProvider>
    );
    // FY 2027-28 full-year figure: $1,981.1M -> $1.98B
    expect(screen.getByText('$1.98B')).toBeInTheDocument();
    // FY 2026-27 half-year figure: $963.2M -> $963M
    expect(screen.getByText('$963M')).toBeInTheDocument();
  });

  it('shows a pending placeholder for the model revenue before the precompute runs', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ValidationMethodology />
      </QueryClientProvider>
    );
    expect(screen.getByText(/Pending/)).toBeInTheDocument();
  });

  it('lists the three key modeling limitations', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ValidationMethodology />
      </QueryClientProvider>
    );
    expect(screen.getByText('Home-sale carve-out unmodeled')).toBeInTheDocument();
    expect(
      screen.getByText('Corporate and TABOR sections out of scope')
    ).toBeInTheDocument();
    expect(
      screen.getByText('District geography is PUMA-based')
    ).toBeInTheDocument();
  });

  it('names the Populace build P ACS-local dataset revision', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ValidationMethodology />
      </QueryClientProvider>
    );
    expect(
      screen.getByText('populace-us-2024-buildp-acs-local-592ae5d6-20260819T020303Z')
    ).toBeInTheDocument();
    expect(
      screen.getByText('populace_us_2024_acs_local.h5')
    ).toBeInTheDocument();
  });

  it('links to the fiscal impact statement, measure text, and model PR', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ValidationMethodology />
      </QueryClientProvider>
    );
    const links = screen.getAllByRole('link');
    const hrefs = links.map((l) => l.getAttribute('href'));
    expect(hrefs).toContain('https://leg.colorado.gov/initiative_files/3320/download');
    expect(hrefs).toContain(
      'https://www.sos.state.co.us/pubs/elections/Initiatives/titleBoard/filings/2025-2026/195Final.pdf'
    );
    expect(hrefs).toContain('https://github.com/PolicyEngine/policyengine-us/pull/9431');
  });

  it('documents the reform parameter and pin', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ValidationMethodology />
      </QueryClientProvider>
    );
    expect(
      screen.getByText('gov.contrib.states.co.progressive_income_tax.in_effect')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/policyengine-us==1\.825\.0/)
    ).toBeInTheDocument();
  });
});
