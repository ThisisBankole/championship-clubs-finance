import React from "react";
import ClubCard from "./ClubCard";

const ClubGrid = ({ clubs }) => {
  const validClubs = clubs
    .filter(
      (club) =>
        club.club_name &&
        club.club_name.trim() !== "" &&
        club.club_name !== null &&
        club.club_name !== "Data" &&
        club.club_name !== "test" &&
        club.company_number !== "market" &&
        club.company_number !== "test"
    )
    .sort((a, b) => a.club_name.localeCompare(b.club_name)); 

  return (
    <div className="container-fluid px-4 mt-5">
      <div className="row justify-content-center">
        <div className="col-12 col-md-8 col-lg-6">
          <div className="dark-container">
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
