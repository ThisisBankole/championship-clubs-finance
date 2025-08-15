// src/components/ClubCard.js
import React from 'react';
import { Link } from 'react-router-dom';

const ClubCard = ({ club }) => {
  // Championship 2025/26 clubs with broadcasting codes
  const broadcastingCodes = {
    'Blackburn Rovers': { code: 'BLB', color: 'primary' },
    'Bristol City': { code: 'BRI', color: 'danger' },
    'Coventry City': { code: 'COV', color: 'info' },
    'Derby County': { code: 'DER', color: 'dark' },
    'Hull City': { code: 'HUL', color: 'warning' },
    'Leicester City': { code: 'LEI', color: 'primary' },
    'Middlesbrough': { code: 'MID', color: 'danger' },
    'Millwall': { code: 'MIL', color: 'primary' },
    'Norwich City': { code: 'NOR', color: 'warning' },
    'Oxford United': { code: 'OXF', color: 'warning' },
    'Portsmouth': { code: 'POR', color: 'primary' },
    'Preston North End': { code: 'PRE', color: 'light' },
    'Queens Park Rangers': { code: 'QPR', color: 'primary' },
    'Sheffield United': { code: 'SHU', color: 'danger' },
    'Sheffield Wednesday': { code: 'SHW', color: 'primary' },
    'Stoke City': { code: 'STK', color: 'danger' },
    'Swansea City': { code: 'SWA', color: 'light' },
    'Watford': { code: 'WAT', color: 'warning' },
    'West Bromwich Albion': { code: 'WBA', color: 'primary' },
    'Ipswich Town': { code: 'IPS', color: 'primary' },
    'Southampton': { code: 'SOU', color: 'danger' },
    'Birmingham City': { code: 'BIR', color: 'primary' },
    'Wrexham': { code: 'WRX', color: 'danger' },
    'Charlton Athletic': { code: 'CHA', color: 'danger' }
  };

  // Check if club_name is valid
  if (!club.club_name || club.club_name.trim() === '' || club.club_name === null) {
    return null;
  }

  const clubInfo = broadcastingCodes[club.club_name] || { code: 'UNK', color: 'secondary' };

  return (
    <Link to={`/club/${encodeURIComponent(club.club_name)}`} className="text-decoration-none">
      <div className="card border-0 shadow-sm mb-2 h-100" style={{ transition: 'transform 0.2s' }}>
        <div className="card-body py-3">
          <div className="row align-items-center">
            {/* Broadcasting Code */}
            <div className="col-auto">
              <span className={`badge bg-${clubInfo.color} fs-6 fw-bold px-3 py-2`}
                    style={{ minWidth: '60px', fontFamily: 'var(--font-mono)' }}>
                {clubInfo.code}
              </span>
            </div>
            
            {/* Club Name */}
            <div className="col">
              <h6 className="mb-0 fw-semibold text-dark" style={{ fontFamily: 'var(--font-mono)' }}>
                {club.club_name}
              </h6>
            </div>
            
            {/* Arrow indicator */}
            <div className="col-auto">
              <i className="bi bi-chevron-right text-muted"></i>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
};

export default ClubCard;