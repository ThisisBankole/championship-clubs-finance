import React from 'react';

const ClubCard = ({ club }) => {
  return (
    <div style={{
      border: '1px solid #ddd',
      borderRadius: '8px',
      padding: '20px',
      margin: '8px',
      backgroundColor: 'white',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      cursor: 'pointer',
      textAlign: 'center'
    }}>
      <h3 style={{ 
        margin: 0, 
        color: '#333',
        fontSize: '18px' 
      }}>
        {club.club_name}
      </h3>
    </div>
  );
};

export default ClubCard;