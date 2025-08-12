import React from 'react';
import ClubCard from './ClubCard';

const ClubGrid = ({ clubs }) => {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
      gap: '16px',
      padding: '16px'
    }}>
      {clubs.map((club, index) => (
        <ClubCard key={club.id || index} club={club} />
      ))}
    </div>
  );
};

export default ClubGrid;