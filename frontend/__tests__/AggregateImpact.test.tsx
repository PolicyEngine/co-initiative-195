import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AggregateImpact from '../components/AggregateImpact';

// Mock fetch for CSV loading — plain (no _revert) filenames per
// scripts/DATA_SCHEMA.md, single year 2027, forward sign convention
// (positive revenue = revenue increase; negative household change =
// tax increase).
const mockMetricsCSV = `year,metric,value
2027,budgetary_impact,2100000000
2027,federal_tax_revenue_impact,150000000
2027,state_tax_revenue_impact,2000000000
2027,tax_revenue_impact,2100000000
2027,households,2300000
2027,avg_household_net_income_change,-913
2027,total_cost,-2100000000
2027,beneficiaries,1500000
2027,avg_benefit,85
2027,winners,1500000
2027,losers,700000
2027,winners_rate,65.2
2027,losers_rate,30.4
2027,poverty_baseline_rate,9.5
2027,poverty_reform_rate,9.5
2027,poverty_rate_change,0
2027,poverty_percent_change,0
2027,child_poverty_baseline_rate,11.2
2027,child_poverty_reform_rate,11.2
2027,child_poverty_rate_change,0
2027,child_poverty_percent_change,0
2027,deep_poverty_baseline_rate,3.8
2027,deep_poverty_reform_rate,3.8
2027,deep_poverty_rate_change,0
2027,deep_poverty_percent_change,0
2027,deep_child_poverty_baseline_rate,4.1
2027,deep_child_poverty_reform_rate,4.1
2027,deep_child_poverty_rate_change,0
2027,deep_child_poverty_percent_change,0`;

const mockDistributionalCSV = `year,decile,average_change,relative_change
2027,1,45,0.002
2027,2,60,0.002
2027,3,70,0.002
2027,4,80,0.002
2027,5,85,0.001
2027,6,90,0.001
2027,7,95,0.001
2027,8,100,0.001
2027,9,60,0
2027,10,-9500,-0.02`;

const mockWinnersLosersCSV = `year,decile,gain_more_5pct,gain_less_5pct,no_change,lose_less_5pct,lose_more_5pct
2027,All,0.01,0.64,0.05,0.25,0.05
2027,1,0.05,0.75,0.2,0,0
2027,2,0.02,0.78,0.2,0,0
2027,3,0.01,0.79,0.2,0,0
2027,4,0.01,0.79,0.2,0,0
2027,5,0,0.8,0.2,0,0
2027,6,0,0.8,0.2,0,0
2027,7,0,0.8,0.2,0,0
2027,8,0,0.8,0.2,0,0
2027,9,0,0.75,0.2,0.05,0
2027,10,0,0.1,0.1,0.5,0.3`;

const mockIncomeBracketsCSV = `year,bracket,households,beneficiaries,total_cost,avg_benefit
2027,$0 - $25k,300000,250000,20000000,67
2027,$25k - $50k,350000,300000,35000000,100
2027,$50k - $75k,320000,280000,40000000,125
2027,$75k - $100k,280000,240000,35000000,125
2027,$100k - $200k,500000,300000,10000000,20
2027,$200k - $500k,350000,100000,-50000000,-143
2027,$500k - $750k,60000,0,-500000000,-8333
2027,$750k - $1M,25000,0,-450000000,-18000
2027,$1M+,30000,0,-1240000000,-41333`;

beforeEach(() => {
  global.fetch = vi.fn((url: string) => {
    if (url.includes('metrics.csv')) {
      return Promise.resolve({ ok: true, text: () => Promise.resolve(mockMetricsCSV) });
    }
    if (url.includes('distributional_impact.csv')) {
      return Promise.resolve({ ok: true, text: () => Promise.resolve(mockDistributionalCSV) });
    }
    if (url.includes('winners_losers.csv')) {
      return Promise.resolve({ ok: true, text: () => Promise.resolve(mockWinnersLosersCSV) });
    }
    if (url.includes('income_brackets.csv')) {
      return Promise.resolve({ ok: true, text: () => Promise.resolve(mockIncomeBracketsCSV) });
    }
    return Promise.resolve({ ok: false, status: 404 });
  }) as typeof fetch;
});

// Mock ResizeObserver for Recharts
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('AggregateImpact', () => {
  it('renders nothing when not triggered', () => {
    const queryClient = createTestQueryClient();
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <AggregateImpact triggered={false} />
      </QueryClientProvider>
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows loading state when triggered', () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <AggregateImpact triggered={true} />
      </QueryClientProvider>
    );
    expect(screen.getByText('Loading Colorado statewide data...')).toBeInTheDocument();
  });

  it('renders the fiscal cards from the plain-named CSVs', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <AggregateImpact triggered={true} />
      </QueryClientProvider>
    );
    expect(
      await screen.findByText('Colorado state revenue change')
    ).toBeInTheDocument();
    // state_tax_revenue_impact = +$2.0B (revenue increase)
    expect(screen.getByText('+$2.0B')).toBeInTheDocument();
    // total_cost = -$2.1B (household-side mirror)
    expect(screen.getByText('-$2.1B')).toBeInTheDocument();
  });

  it('shows the unavailable-data panel when CSVs are missing', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 404 })
    ) as typeof fetch;
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <AggregateImpact triggered={true} />
      </QueryClientProvider>
    );
    expect(
      await screen.findByText('Statewide impact data not yet available')
    ).toBeInTheDocument();
  });
});
