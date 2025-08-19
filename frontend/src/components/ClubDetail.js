import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { clubsApi, clubDescriptionsApi } from '../services/api';
import { clubNameToSlug } from '../utils/clubUtils';

const ClubDetail = () => {
  const { clubName } = useParams();
  const [club, setClub] = useState(null);
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

  // Data classification function
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
      {/* Universal Header - All clubs get this */}
      
      <ClubHeader club={club} description={description} />
      
      {/* Adaptive Content based on data tier */}
      {dataTier === 'rich' && <RichDataView club={club} formatCurrency={formatCurrency} />}
      {dataTier === 'core' && <CoreDataView club={club} />}
      {dataTier === 'basic' && <BasicDataView club={club} />}
    </div>
  );
};

// Universal header component
const ClubHeader = ({ club, description }) => {
  return (
    <div className="row mb-4">
      <div className="col-12">
        <div className="card border-0 shadow-sm">
          <div className="card-body">
            <div className="d-flex justify-content-between align-items-center">
              <div>
                <h1 className="h2 mb-2" style={{ fontFamily: 'var(--font-mono)' }}>
                  {club.club_name}
                </h1>

                {/* Add description here */}
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
    <div className="card border-0 shadow-sm mb-4">
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
    <div className="card border-0 shadow-sm mb-4">
     
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

const ClubContext = ({ club }) => {
  return (
    <div className="card border-0 shadow-sm">
      <div className="card-header bg-white">
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
    <div className="card border-0 shadow-sm">
      <div className="card-header bg-white">
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
    <div className="card border-0 shadow-sm">
      <div className="card-header bg-white">
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
    <div className="col-12">
      <FinancialHighlights club={club} />
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
    
    // Admin Costs as % of Revenue
    if (club.administrative_expenses && club.revenue) {
      metrics.adminPercentage = (Math.abs(club.administrative_expenses) / club.revenue) * 100;
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
          <div className="card border-0 shadow-sm mb-4">
            
            <div className="card-body">
              <div className="row mb-3">
                <div className="col-md-6">
                  <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                    TOTAL REVENUE
                  </div>
                  <div style={{ fontSize: '24px', fontWeight: '600', margin: 0, color: '#198754' }}>
                    {formatCurrency(club.revenue)}
                  </div>
                </div>
              </div>
              
              <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                REVENUE BREAKDOWN
              </div>
              
              {/* Revenue visualization bar */}
              <div style={{
                height: '200px',
                background: `linear-gradient(90deg, 
                  #0d6efd 0% ${revenueBreakdown.broadcasting.percentage}%, 
                  #198754 ${revenueBreakdown.broadcasting.percentage}% ${revenueBreakdown.broadcasting.percentage + revenueBreakdown.commercial.percentage}%, 
                  #fd7e14 ${revenueBreakdown.broadcasting.percentage + revenueBreakdown.commercial.percentage}% ${revenueBreakdown.broadcasting.percentage + revenueBreakdown.commercial.percentage + revenueBreakdown.matchday.percentage}%, 
                  #6c757d ${revenueBreakdown.broadcasting.percentage + revenueBreakdown.commercial.percentage + revenueBreakdown.matchday.percentage}% 100%)`,
                borderRadius: '4px',
                position: 'relative'
              }}></div>

              
              {/* Revenue legend */}
              <div style={{ display: 'flex', gap: '15px', marginTop: '10px', flexWrap: 'wrap' }}>
                {club.broadcasting_revenue && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '2px', background: '#0d6efd' }}></div>
                    <span>Broadcasting: {formatCurrency(club.broadcasting_revenue)} ({Math.round(revenueBreakdown.broadcasting.percentage)}%)</span>
                  </div>
                )}
                {club.commercial_revenue && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '2px', background: '#198754' }}></div>
                    <span>Commercial: {formatCurrency(club.commercial_revenue)} ({Math.round(revenueBreakdown.commercial.percentage)}%)</span>
                  </div>
                )}
                {club.matchday_revenue && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '2px', background: '#fd7e14' }}></div>
                    <span>Matchday: {formatCurrency(club.matchday_revenue)} ({Math.round(revenueBreakdown.matchday.percentage)}%)</span>
                  </div>
                )}
                {revenueBreakdown.other.amount > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
                    <div style={{ width: '12px', height: '12px', borderRadius: '2px', background: '#6c757d' }}></div>
                    <span>Other: {formatCurrency(revenueBreakdown.other.amount)} ({Math.round(revenueBreakdown.other.percentage)}%)</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Operating Performance  */}
        {hasOperatingData && (
          <div className="card border-0 shadow-sm mb-4">
            <div className="card-body">
             
              
              <div className="row">
                {club.operating_profit !== null && club.operating_profit !== undefined && (
                  <div className="col-md-4">
                    <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                      OPERATING PROFIT/LOSS
                    </div>
                    <div style={{ fontSize: '24px', fontWeight: '600', margin: 0, color: club.operating_profit >= 0 ? '#198754' : '#dc3545' }}>
                      {formatCurrency(club.operating_profit)}
                    </div>
                  </div>
                )}
                
                {metrics.operatingMargin !== undefined && (
                  <div className="col-md-4">
                    <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                      OPERATING MARGIN
                    </div>
                    <div style={{ fontSize: '24px', fontWeight: '600', margin: 0, color: metrics.operatingMargin >= 0 ? '#198754' : '#dc3545' }}>
                      {Math.round(metrics.operatingMargin)}%
                    </div>
                  </div>
                )}

                {club.profit_loss_before_tax !== null && club.profit_loss_before_tax !== undefined && (
                        <div className="col-md-4">
                          <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                            PROFIT/LOSS BEFORE TAX
                          </div>
                          <div style={{ fontSize: '24px', fontWeight: '600', margin: 0, color: club.profit_loss_before_tax >= 0 ? '#198754' : '#dc3545' }}>
                            {formatCurrency(club.profit_loss_before_tax)}
                          </div>
                        </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Player Business - NEW */}
        {hasPlayerData && (
          <div className="card border-0 shadow-sm mb-4">
            <div className="card-body">
             
              
              <div className="row">
                {club.profit_on_player_disposals && (
                  <div className="col-md-4">
                    <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                      PLAYER TRADING INCOME
                    </div>
                    <div style={{ fontSize: '24px', fontWeight: '600', margin: 0, color: '#198754' }}>
                      {formatCurrency(club.profit_on_player_disposals)}
                    </div>
                  </div>
                )}
                
                {club.player_wages && (
                  <div className="col-md-4">
                    <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                      PLAYER WAGES
                    </div>
                    <div style={{ fontSize: '24px', fontWeight: '600', margin: 0, color: '#dc3545' }}>
                      {formatCurrency(Math.abs(club.player_wages))}
                    </div>
                  </div>
                )}
                
                {metrics.playerInvestmentEfficiency !== undefined && (
                  <div className="col-md-4">
                    <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                      PLAYER INVESTMENT EFFICIENCY
                    </div>
                    <div style={{ fontSize: '24px', fontWeight: '600', margin: 0, color: metrics.playerInvestmentEfficiency >= 1 ? '#198754' : '#dc3545' }}>
                      {metrics.playerInvestmentEfficiency.toFixed(1)}x
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    

      {/* Sidebar - NEW */}
      <div className="col-md-4">
        {/* Key Ratios */}
        {(metrics.wagesPercentage || metrics.adminPercentage || metrics.operatingMargin) && (
          <div className="card border-0 shadow-sm mb-4">
            <div className="card-body">
             
              
              {metrics.wagesPercentage !== undefined && (
                <div className="mb-3">
                  <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                    WAGES % OF REVENUE
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: '600', margin: 0, color: metrics.wagesPercentage > 70 ? '#dc3545' : '#6c757d' }}>
                    {Math.round(metrics.wagesPercentage)}%
                  </div>
                </div>
              )}
              
              {metrics.adminPercentage !== undefined && (
                <div className="mb-3">
                  <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                    ADMIN % OF REVENUE
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: '600', margin: 0, color: '#6c757d' }}>
                    {Math.round(metrics.adminPercentage)}%
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Cost Structure */}
        {hasCostData && (
          <div className="card border-0 shadow-sm mb-4">
            <div className="card-body">
            
              
              {metrics.totalOperatingCosts && (
                <div className="mb-3">
                  <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                    TOTAL OPERATING COSTS
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: '600', margin: 0, color: '#dc3545' }}>
                    {formatCurrency(metrics.totalOperatingCosts)}
                  </div>
                </div>
              )}
              
              {club.administrative_expenses && (
                <div className="mb-3">
                  <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                    ADMINISTRATIVE EXPENSES
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: '600', margin: 0, color: '#6c757d' }}>
                    {formatCurrency(Math.abs(club.administrative_expenses))}
                  </div>
                </div>
              )}

              {club.staff_costs_total && (
                <div className="mb-3">
                  <div style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                    STAFF COST
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: '600', margin: 0, color: '#6c757d' }}>
                    {formatCurrency(Math.abs(club.staff_costs_total))}
                  </div>
                </div>
              )}
              
              
            </div>
          </div>
        )}
      </div>

      {/* If no performance data available */}
      {!hasRevenueBreakdown && !hasOperatingData && !hasPlayerData && !hasCostData &&(
        <div className="col-12">
          <div className="card border-0 shadow-sm">
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