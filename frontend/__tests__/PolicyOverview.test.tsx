import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import PolicyOverview from '../components/PolicyOverview';

describe('PolicyOverview', () => {
  it('renders the measure heading', () => {
    render(<PolicyOverview />);
    expect(
      screen.getByText('Colorado Initiative 195 (Amendment 87)')
    ).toBeInTheDocument();
  });

  it('displays all six bracket rates', () => {
    render(<PolicyOverview />);
    for (const rate of ['3.7%', '4.2%', '7.4%', '7.9%', '8.4%']) {
      expect(screen.getByText(rate)).toBeInTheDocument();
    }
    // 4.4% appears both as the current flat rate and as a bracket rate.
    expect(screen.getAllByText('4.4%').length).toBeGreaterThan(1);
  });

  it('displays the bracket thresholds', () => {
    render(<PolicyOverview />);
    expect(screen.getByText('$0 – $25,000')).toBeInTheDocument();
    expect(screen.getByText('$25,000 – $100,000')).toBeInTheDocument();
    expect(screen.getByText('$100,000 – $500,000')).toBeInTheDocument();
    expect(screen.getByText('$500,000 – $750,000')).toBeInTheDocument();
    expect(screen.getByText('$750,000 – $1,000,000')).toBeInTheDocument();
    expect(screen.getByText('Over $1,000,000')).toBeInTheDocument();
  });

  it('links to the official measure text and the model PR', () => {
    render(<PolicyOverview />);
    const sosLink = screen.getByRole('link', {
      name: 'Final text (Colorado Secretary of State)',
    });
    expect(sosLink).toHaveAttribute(
      'href',
      'https://www.sos.state.co.us/pubs/elections/Initiatives/titleBoard/filings/2025-2026/195Final.pdf'
    );
    const prLink = screen.getByRole('link', { name: 'PR #9431' });
    expect(prLink).toHaveAttribute(
      'href',
      'https://github.com/PolicyEngine/policyengine-us/pull/9431'
    );
  });

  it('states the effective year and ballot timing', () => {
    render(<PolicyOverview />);
    expect(
      screen.getByText(/effective tax year 2027/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/November 2026 ballot/i)).toBeInTheDocument();
  });
});
