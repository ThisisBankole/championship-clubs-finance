import React from 'react';
import ClubCard from './ClubCard';

const ClubGrid = ({ clubs }) => {

   


  // Filter out clubs with invalid names
  const validClubs = clubs.filter(club => 
    club.club_name && 
    club.club_name.trim() !== '' && 
    club.club_name !== null &&
    club.club_name !== 'Data' &&      
    club.club_name !== 'test' &&        
    club.company_number !== 'market' &&  
    club.company_number !== 'test'      
  );
 


  return (
    <div className="container-fluid px-4">
      <div className="row">
        <div className="col-12">
         
          <div className="list-group list-group-flush">
            {validClubs.map((club, index) => (
              <ClubCard key={club.id || index} club={club} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClubGrid;