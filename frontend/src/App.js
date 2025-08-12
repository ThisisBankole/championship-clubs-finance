import React, { useState, useEffect } from 'react';
import { clubsApi } from './services/api';
import ClubGrid from './components/ClubGrid';
import './App.css';

function App() {
  const [clubs, setClubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchClubs = async () => {
      try {
        const response = await clubsApi.getAllClubs();
        setClubs(response.data.clubs);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch clubs');
        setLoading(false);
      }
    };

    fetchClubs();
  }, []);

  if (loading) return <div style={{ padding: '20px' }}>Loading clubs...</div>;
  if (error) return <div style={{ padding: '20px', color: 'red' }}>Error: {error}</div>;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <header style={{ 
        backgroundColor: 'white', 
        padding: '20px', 
        borderBottom: '1px solid #ddd'
      }}>
        <h1 style={{ margin: 0, color: '#333' }}>Football Finance Dashboard</h1>
        <p style={{ margin: '8px 0 0 0', color: '#666' }}>
          {clubs.length} Championship Clubs
        </p>
      </header>
      
      <ClubGrid clubs={clubs} />
    </div>
  );
}

export default App;