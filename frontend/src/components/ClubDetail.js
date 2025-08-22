import React, { useState, useEffect } from 'react';
import { useParams , useNavigate} from 'react-router-dom';
import { clubsApi, clubDescriptionsApi } from '../services/api';
import { clubNameToSlug } from '../utils/clubUtils';


const ClubDetail = () => {
  const { clubName } = useParams();
  const [club, setClub] = useState(null);
  const navigate = useNavigate();
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchClub = async () => {
      try {
        const response = await clubsApi.getClubByName(clubName);
        
        if (response.data.documents && response.data.documents.length > 0) {
          setClub(response.data.documents[0]); 

          try {
            const clubSlug = clubNameToSlug(response.data.documents[0].club_name);
            const descResponse = await clubDescriptionsApi.getDescriptionBySlug(clubSlug);
            
            if (descResponse.data.data.length > 0) {
              setDescription(descResponse.data.data[0].description);
            }
          } catch (descError) {
            console.log('Description not found for', response.data.documents[0].club_name);
          }

        } else {
          setError('Club data not found');
        }
        setLoading(false);
      } catch (err) {
        setError('Club not found');
        setLoading(false);
      }
    };

    fetchClub();
  }, [clubName]);

  const getDataTier = (club) => {
    if (!club) return 'basic';
    
    const richDataFields = ['revenue', 'total_assets', 'operating_expenses', 'net_income', 'total_equity'];
    const coreDataFields = ['revenue', 'total_assets'];
    
    const richFieldsPresent = richDataFields.filter(field => club[field] !== null && club[field] !== undefined).length;
    const coreFieldsPresent = coreDataFields.filter(field => club[field] !== null && club[field] !== undefined).length;
    
    if (richFieldsPresent >= 2) return 'rich';
    if (coreFieldsPresent >= 1) return 'core';
    return 'basic';
  };

  const formatCurrency = (amount) => {
    if (!amount) return null;
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
      notation: amount > 1000000 ? 'compact' : 'standard',
      compactDisplay: 'short'
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center min-vh-100">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading club details...</span>
        </div>
      </div>
    );
  }

  if (error || !club) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger" role="alert">
          <h4 className="alert-heading">Club Not Found</h4>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const dataTier = getDataTier(club);

  return (
    <div className="container mt-4">
      <ClubHeader club={club} description={description} navigate={navigate} />
      
      {dataTier === 'rich' && <RichDataView club={club} formatCurrency={formatCurrency} />}
      {dataTier === 'core' && <CoreDataView club={club} />}
      {dataTier === 'basic' && <BasicDataView club={club} />}
    </div>
  );
};

// Universal header component
const ClubHeader = ({ club, description , navigate}) => {
  return (
    
    <div className="row mb-4">
      
      <div className="col-12">
        <button 
            onClick={() => navigate(-1)}
            className="btn btn-link text-muted p-0 mb-3"
            style={{ textDecoration: 'none' }}
          >
            <i className="bi bi-arrow-left me-2" style={{ fontSize: '18px' }}></i>
            Back
          </button>


        <div className="card">
          <div className="card-body">
            <div className="d-flex justify-content-between align-items-center">
              <div className="d-flex align-items-center">
               
              <div>
                <h1 className="h2 mb-2" style={{ fontFamily: 'var(--font-slab)' }}>
                  {club.club_name}
                </h1>

                {description && (
                  <p className="text-muted mb-0" style={{ 
                    fontSize: '12px', 
                    lineHeight: '1.5',
                    maxWidth: '800px' 
                  }}>
                    {description}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>
  );
};

// Rich data view - Multiple sections and tabs
const RichDataView = ({ club, formatCurrency }) => {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <>
      {/* Tab Navigation */}
      <div className="row mb-4">
        <div className="col-12">
          <ul className="nav nav-tabs">
            <li className="nav-item">
              <button 
                className={`nav-link ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                Overview
              </button>
            </li>
            <li className="nav-item">
              <button 
                className={`nav-link ${activeTab === 'performance' ? 'active' : ''}`}
                onClick={() => setActiveTab('performance')}
              >
                Performance
              </button>
            </li>
           
          </ul>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && <OverviewTab club={club} formatCurrency={formatCurrency} />}
      {activeTab === 'performance' && <PerformanceTab club={club} formatCurrency={formatCurrency} />}
    </>
  );
};

// Core data view - Single comprehensive view
const CoreDataView = ({ club }) => {
  return (
    <div className="row">
      <div className="col-md-8">
        <FinancialHighlights club={club} />
      </div>
      <div className="col-md-4">
        <ClubContext club={club} />
      </div>
    </div>
  );
};

// Basic data view - Essential information only
const BasicDataView = ({ club }) => {
  return (
    <div className="row">
      <div className="col-md-6">
        <EssentialInfo club={club} />
      </div>
      <div className="col-md-6">
        <MarketData club={club} />
      </div>
    </div>
  );
};

// Reusable components
const FinancialHighlights = ({ club }) => {
  const formatCurrency = (amount) => {
    if (!amount) return 'Not disclosed';
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
      notation: 'compact',
      compactDisplay: 'short'
    }).format(amount);
  };

  return (
    <div className="card mb-4">
      <div className="card-body">
        <div className="row g-3">
          {club.total_assets && (
            <div className="col-md-6">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">TOTAL ASSETS</h6>
                <div className="h4 mb-0 text-success">{formatCurrency(club.total_assets)}</div>
              </div>
            </div>
          )}
          
          {club.total_liabilities && (
            <div className="col-md-6">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">TOTAL LIABILITIES</h6>
                <div className={`h4 mb-0 ${club.total_liabilities >= 0 ? 'text-success' : 'text-danger'}`}>
                  {formatCurrency(club.total_liabilities)}
                </div>
              </div>
            </div>
          )}

          {club.total_equity && (
            <div className="col-md-6">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">TOTAL EQUITY</h6>
                <div className={`h4 mb-0 ${club.total_equity >= 0 ? 'text-success' : 'text-warning'}`}>
                  {formatCurrency(club.total_equity)}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const PlayersMarketValue = ({ club, formatCurrency }) => {
  // Only show if market data is available
  if (!club.current_market_value_gbp && !club.championship_position && !club.market_value_change) {
    return null;
  }

  return (
    <div className="card mb-4">
      <div className="card-body">
        <div className="row g-1">
          {club.current_market_value_gbp && (
            <div className="col-md-12">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">SQUAD MARKET VALUE</h6>
                <div className="h4 mb-0 text-primary">{formatCurrency(club.current_market_value_gbp)}</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Add this new component after your existing components
const FinancialRatios = ({ club }) => {
  // Calculate ratios
  const calculateRatios = () => {
    const ratios = {};
    
    // Return on Equity (ROE)
    if (club.operating_profit && club.net_assets && club.net_assets !== 0) {
      ratios.roe = (club.operating_profit / Math.abs(club.net_assets)) * 100;
    }
    
    // Return on Total Assets (ROA)
    if (club.operating_profit && club.total_assets && club.total_assets !== 0) {
      ratios.roa = (club.operating_profit / club.total_assets) * 100;
    }
    
    // Current Ratio
    if (club.current_assets && club.creditors_due_within_one_year && club.creditors_due_within_one_year !== 0) {
      ratios.currentRatio = club.current_assets / Math.abs(club.creditors_due_within_one_year);
    }
    
    // Debt/Equity Ratio
    if (club.total_liabilities && club.net_assets && club.net_assets !== 0) {
      ratios.debtEquity = Math.abs(club.total_liabilities) / Math.abs(club.net_assets);
    }
    
    // Equity/Total Assets
    if (club.net_assets && club.total_assets && club.total_assets !== 0) {
      ratios.equityAssets = (Math.abs(club.net_assets) / club.total_assets) * 100;
    }
    
    // Debt/Total Assets
    if (club.total_liabilities && club.total_assets && club.total_assets !== 0) {
      ratios.debtAssets = (Math.abs(club.total_liabilities) / club.total_assets) * 100;
    }
    
    return ratios;
  };

  const ratios = calculateRatios();
  
  // Don't show if no ratios can be calculated
  if (Object.keys(ratios).length === 0) {
    return null;
  }

  const formatRatio = (value, isPercentage = false, decimals = 1) => {
    if (value === undefined || value === null) return 'N/A';
    if (isPercentage) {
      return `${value.toFixed(decimals)}%`;
    }
    return value.toFixed(decimals);
  };

  const getRatioColor = (ratio, value) => {
    if (value === undefined || value === null) return 'text-muted';
    
    switch (ratio) {
      case 'roe':
        return value > 15 ? 'text-success' : value > 5 ? 'text-warning' : 'text-danger';
      case 'roa':
        return value > 5 ? 'text-success' : value > 2 ? 'text-warning' : 'text-danger';
      case 'currentRatio':
        return value > 1.2 ? 'text-success' : value > 0.8 ? 'text-warning' : 'text-danger';
      case 'debtEquity':
        return value < 1 ? 'text-success' : value < 2 ? 'text-warning' : 'text-danger';
      case 'equityAssets':
        return value > 30 ? 'text-success' : value > 20 ? 'text-warning' : 'text-danger';
      case 'debtAssets':
        return value < 60 ? 'text-success' : value < 80 ? 'text-warning' : 'text-danger';
      default:
        return 'text-muted';
    }
  };

  return (
    <div className="card mb-4">
      <div className="card-body">
    
        <div className="row g-3">
          {/* Row 1 */}
          {ratios.roe !== undefined && (
            <div className="col-md-4">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">RETURN ON EQUITY</h6>
                <div className={`h5 mb-0 ${getRatioColor('roe', ratios.roe)}`}>
                  {formatRatio(ratios.roe, true)}
                </div>
              </div>
            </div>
          )}
          
          {ratios.roa !== undefined && (
            <div className="col-md-4">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">RETURN ON ASSETS</h6>
                <div className={`h5 mb-0 ${getRatioColor('roa', ratios.roa)}`}>
                  {formatRatio(ratios.roa, true)}
                </div>
              </div>
            </div>
          )}
          
          {ratios.currentRatio !== undefined && (
            <div className="col-md-4">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">CURRENT RATIO</h6>
                <div className={`h5 mb-0 ${getRatioColor('currentRatio', ratios.currentRatio)}`}>
                  {formatRatio(ratios.currentRatio, false, 2)}
                </div>
              </div>
            </div>
          )}

          {/* Row 2 */}
          {ratios.debtEquity !== undefined && (
            <div className="col-md-4">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">DEBT/EQUITY RATIO</h6>
                <div className={`h5 mb-0 ${getRatioColor('debtEquity', ratios.debtEquity)}`}>
                  {formatRatio(ratios.debtEquity, false, 2)}
                </div>
              </div>
            </div>
          )}
          
          {ratios.equityAssets !== undefined && (
            <div className="col-md-4">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">EQUITY/TOTAL ASSETS</h6>
                <div className={`h5 mb-0 ${getRatioColor('equityAssets', ratios.equityAssets)}`}>
                  {formatRatio(ratios.equityAssets, true)}
                </div>
              </div>
            </div>
          )}
          
          {ratios.debtAssets !== undefined && (
            <div className="col-md-4">
              <div className="border rounded p-3">
                <h6 className="text-muted small mb-1">DEBT/TOTAL ASSETS</h6>
                <div className={`h5 mb-0 ${getRatioColor('debtAssets', ratios.debtAssets)}`}>
                  {formatRatio(ratios.debtAssets, true)}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const ClubContext = ({ club }) => {
  return (
    <div className="card">
      <div className="card-header">
        <h6 className="mb-0">About This Data</h6>
      </div>
      <div className="card-body">
        <p className="small text-muted mb-0">
          Financial data is extracted from official Companies House filings for the year ending {club.accounts_year_end}.
        </p>
      </div>
    </div>
  );
};

const EssentialInfo = ({ club }) => {
  return (
    <div className="card">
      <div className="card-header">
        <h5 className="mb-0">Essential Information</h5>
      </div>
      <div className="card-body">
        <div className="row g-2">
          <div className="col-12">
            <small className="text-muted">Company Number</small>
            <div className="fw-bold">{club.company_number}</div>
          </div>
          <div className="col-12">
            <small className="text-muted">Accounts Filed</small>
            <div className="fw-bold">{club.accounts_year_end}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

const MarketData = ({ club }) => {
  return (
    <div className="card">
      <div className="card-header">
        <h5 className="mb-0">Market Information</h5>
      </div>
      <div className="card-body">
        <p className="text-muted small">
          Market value and performance data will be displayed here when available.
        </p>
      </div>
    </div>
  );
};

// Tab components for rich data view
const OverviewTab = ({ club, formatCurrency }) => (
  <div className="row">
    <div className="col-md-8">
      <FinancialHighlights club={club} />
      <FinancialRatios club={club} />
     
    </div>
    <div className="col-md-4">
      <PlayersMarketValue club={club} formatCurrency={formatCurrency} />
     
    </div>
  </div>
);

const PerformanceTab = ({ club, formatCurrency }) => {
  // Only show sections with available data
  const hasRevenueBreakdown = club.broadcasting_revenue || club.commercial_revenue || club.matchday_revenue;
  const hasOperatingData = club.operating_profit !== null || club.operating_profit !== undefined;
  const hasPlayerData = club.profit_on_player_disposals || club.player_wages || club.player_amortization;
  const hasCostData = club.administrative_expenses || club.profit_loss_before_tax;
  const hasCashFlowData = club.operating_cash_flow || club.investing_cash_flow || club.financing_cash_flow; 

  // Calculate revenue breakdown percentages
  const calculateRevenuePercentages = () => {
    const total = club.revenue || 0;
    const broadcasting = club.broadcasting_revenue || 0;
    const commercial = club.commercial_revenue || 0;
    const matchday = club.matchday_revenue || 0;
    const other = total - (broadcasting + commercial + matchday);

    return {
      broadcasting: { amount: broadcasting, percentage: total > 0 ? (broadcasting / total) * 100 : 0 },
      commercial: { amount: commercial, percentage: total > 0 ? (commercial / total) * 100 : 0 },
      matchday: { amount: matchday, percentage: total > 0 ? (matchday / total) * 100 : 0 },
      other: { amount: other, percentage: total > 0 ? (other / total) * 100 : 0 }
    };
  };

  const calculateMetrics = () => {
    const metrics = {};
    
    // Operating Margin
    if (club.operating_profit !== null && club.revenue) {
      metrics.operatingMargin = (club.operating_profit / club.revenue) * 100;
    }
    
    // Player Wages as % of Revenue
    if (club.player_wages && club.revenue) {
      metrics.wagesPercentage = (Math.abs(club.player_wages) / club.revenue) * 100;
    }
    
  
   
    
    // Total Operating Costs
    if (club.administrative_expenses || club.player_wages || club.staff_costs_total) {
      const adminCosts = Math.abs(club.administrative_expenses) || 0;
      const playerWages = Math.abs(club.player_wages) || 0;
      const staffCosts = Math.abs(club.staff_costs_total) || 0;
      
      // Use player_wages if available, otherwise use staff_costs_total
      const laborCosts = playerWages > 0 ? playerWages : staffCosts;
      
      metrics.totalOperatingCosts = adminCosts + laborCosts;
    }
    
    // Player Investment Efficiency
    if (club.profit_on_player_disposals && club.player_amortization) {
      metrics.playerInvestmentEfficiency = club.profit_on_player_disposals / Math.abs(club.player_amortization);
    }
    
    return metrics;
  };

  const revenueBreakdown = hasRevenueBreakdown ? calculateRevenuePercentages() : null;
  const metrics = calculateMetrics();

  return (
    <div className="row">
      <div className="col-md-8">
        {/* Revenue Sources Breakdown with visualization */}
        {hasRevenueBreakdown && (
          <div className="card mb-4">
            <div className="card-body">
              <div className="row mb-3">
                <div className="col-md-6">
                  <div className="dark-metric-label">
                    TOTAL REVENUE
                  </div>
                  <div className="dark-metric-value text-success">
                    {formatCurrency(club.revenue)}
                  </div>
                </div>
              </div>
              
              <div className="dark-metric-label mb-2">
                REVENUE BREAKDOWN
              </div>
              
              {/* Revenue visualization bar */}
              <div className="dark-chart-bar" style={{
                height: '20px',
                background: `linear-gradient(90deg, 
                  #0d6efd 0% ${revenueBreakdown.broadcasting.percentage}%, 
                  #198754 ${revenueBreakdown.broadcasting.percentage}% ${revenueBreakdown.broadcasting.percentage + revenueBreakdown.commercial.percentage}%, 
                  #fd7e14 ${revenueBreakdown.broadcasting.percentage + revenueBreakdown.commercial.percentage}% ${revenueBreakdown.broadcasting.percentage + revenueBreakdown.commercial.percentage + revenueBreakdown.matchday.percentage}%, 
                  #6c757d ${revenueBreakdown.broadcasting.percentage + revenueBreakdown.commercial.percentage + revenueBreakdown.matchday.percentage}% 100%)`,
                borderRadius: '4px',
                marginBottom: '10px'
              }}></div>

              {/* Revenue legend */}
              <div className="dark-chart-legend">
                {club.broadcasting_revenue && (
                  <div className="dark-legend-item">
                    <div className="dark-legend-color" style={{ background: '#0d6efd' }}></div>
                    <span>Broadcasting: {formatCurrency(club.broadcasting_revenue)} ({Math.round(revenueBreakdown.broadcasting.percentage)}%)</span>
                  </div>
                )}
                {club.commercial_revenue && (
                  <div className="dark-legend-item">
                    <div className="dark-legend-color" style={{ background: '#198754' }}></div>
                    <span>Commercial: {formatCurrency(club.commercial_revenue)} ({Math.round(revenueBreakdown.commercial.percentage)}%)</span>
                  </div>
                )}
                {club.matchday_revenue && (
                  <div className="dark-legend-item">
                    <div className="dark-legend-color" style={{ background: '#fd7e14' }}></div>
                    <span>Matchday: {formatCurrency(club.matchday_revenue)} ({Math.round(revenueBreakdown.matchday.percentage)}%)</span>
                  </div>
                )}
                {revenueBreakdown.other.amount > 0 && (
                  <div className="dark-legend-item">
                    <div className="dark-legend-color" style={{ background: '#6c757d' }}></div>
                    <span>Other: {formatCurrency(revenueBreakdown.other.amount)} ({Math.round(revenueBreakdown.other.percentage)}%)</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Operating Performance */}
        {hasOperatingData && (
          <div className="card mb-4">
            <div className="card-body">
              <div className="row">
                {club.operating_profit !== null && club.operating_profit !== undefined && (
                  <div className="col-md-4">
                    <div className="dark-metric-label">
                      OPERATING PROFIT/LOSS
                    </div>
                    <div className={`dark-metric-value ${club.operating_profit >= 0 ? 'text-success' : 'text-danger'}`}>
                      {formatCurrency(club.operating_profit)}
                    </div>
                  </div>
                )}
                
                {metrics.operatingMargin !== undefined && (
                  <div className="col-md-4">
                    <div className="dark-metric-label">
                      OPERATING MARGIN
                    </div>
                    <div className={`dark-metric-value ${metrics.operatingMargin >= 0 ? 'text-success' : 'text-danger'}`}>
                      {Math.round(metrics.operatingMargin)}%
                    </div>
                  </div>
                )}

                {club.profit_loss_before_tax !== null && club.profit_loss_before_tax !== undefined && (
                  <div className="col-md-4">
                    <div className="dark-metric-label">
                      PROFIT/LOSS BEFORE TAX
                    </div>
                    <div className={`dark-metric-value ${club.profit_loss_before_tax >= 0 ? 'text-success' : 'text-danger'}`}>
                      {formatCurrency(club.profit_loss_before_tax)}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {hasCashFlowData && (
                <div className="card mb-4">
                  <div className="card-body">
                    <div className="row">
                      {club.operating_cash_flow && (
                        <div className="col-md-4">
                          <div className="dark-metric-label">
                            OPERATING CASH FLOW
                          </div>
                          <div className={`dark-metric-value ${club.operating_cash_flow >= 0 ? 'text-success' : 'text-danger'}`}>
                            {formatCurrency(club.operating_cash_flow)}
                          </div>
                        </div>
                      )}
                      
                      {club.investing_cash_flow && (
                        <div className="col-md-4">
                          <div className="dark-metric-label">
                            INVESTING CASH FLOW
                          </div>
                          <div className={`dark-metric-value ${club.investing_cash_flow >= 0 ? 'text-success' : 'text-danger'}`}>
                            {formatCurrency(club.investing_cash_flow)}
                          </div>
                        </div>
                      )}

                      {club.financing_cash_flow && (
                        <div className="col-md-4">
                          <div className="dark-metric-label">
                            FINANCING CASH FLOW
                          </div>
                          <div className={`dark-metric-value ${club.financing_cash_flow >= 0 ? 'text-success' : 'text-danger'}`}>
                            {formatCurrency(club.financing_cash_flow)}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

        {/* Player Business */}
        {hasPlayerData && (
          <div className="card mb-4">
            <div className="card-body">
              <div className="row">
                {club.profit_on_player_disposals && (
                  <div className="col-md-4">
                    <div className="dark-metric-label">
                      PLAYER TRADING INCOME
                    </div>
                    <div className="dark-metric-value text-success">
                      {formatCurrency(club.profit_on_player_disposals)}
                    </div>
                  </div>
                )}
                
                {club.player_wages && (
                  <div className="col-md-4">
                    <div className="dark-metric-label">
                      PLAYER WAGES
                    </div>
                    <div className="dark-metric-value text-danger">
                      {formatCurrency(Math.abs(club.player_wages))}
                    </div>
                  </div>
                )}
                
                {metrics.playerInvestmentEfficiency !== undefined && (
                  <div className="col-md-4">
                    <div className="dark-metric-label">
                      PLAYER INVESTMENT EFFICIENCY
                    </div>
                    <div className={`dark-metric-value ${metrics.playerInvestmentEfficiency >= 1 ? 'text-success' : 'text-danger'}`}>
                      {metrics.playerInvestmentEfficiency.toFixed(1)}x
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Sidebar */}
      <div className="col-md-4">
        {/* Key Ratios */}
      

        {/* Cost Structure */}
        {hasCostData && (
          <div className="card mb-4">
            <div className="card-body">
              {metrics.totalOperatingCosts && (
                <div className="mb-3">
                  <div className="dark-metric-label">
                    TOTAL OPERATING COSTS
                  </div>
                  <div className="dark-metric-value-sm text-danger">
                    {formatCurrency(metrics.totalOperatingCosts)}
                  </div>
                </div>
              )}
              
              {club.administrative_expenses && (
                <div className="mb-3">
                  <div className="dark-metric-label">
                    ADMINISTRATIVE EXPENSES
                  </div>
                  <div className="dark-metric-value-xs text-muted">
                    {formatCurrency(Math.abs(club.administrative_expenses))}
                  </div>
                </div>
              )}

              {club.staff_costs_total && (
                <div className="mb-3">
                  <div className="dark-metric-label">
                    STAFF COST
                  </div>
                  <div className="dark-metric-value-xs text-muted">
                    {formatCurrency(Math.abs(club.staff_costs_total))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* If no performance data available */}
      {!hasRevenueBreakdown && !hasOperatingData && !hasPlayerData && !hasCostData && !hasCashFlowData &&  (
        <div className="col-12">
          <div className="card">
            <div className="card-body text-center py-5">
              <h5 className="text-muted">Performance Details</h5>
              <p className="text-muted mb-0">Detailed performance analysis will be displayed when revenue and cost breakdowns are available.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClubDetail;