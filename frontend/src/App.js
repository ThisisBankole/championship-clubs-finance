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

        console.log('=== API FETCH DEBUG ===');
      

        const response = await clubsApi.getAllClubs();

        console.log('API Response:', response);
        console.log('Response data:', response.data);
        console.log('Clubs array:', response.data.clubs);
        console.log('Number of clubs from API:', response.data.clubs?.length);


        setClubs(response.data.clubs);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch clubs');
        setLoading(false);
      }
    };

    fetchClubs();
  }, []);

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center min-vh-100">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading clubs...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger m-4" role="alert">
        <h4 className="alert-heading">Error</h4>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="min-vh-100" style={{ backgroundColor: '#f8f9fa' }}>
      <nav className="navbar navbar-light bg-white border-bottom">
        <div className="container-fluid px-4">
          <span className="navbar-brand mb-0 h1 fw-bold" style={{ fontFamily: 'var(--font-mono)' }}>
            Football Finance Dashboard
          </span>
          <span className="text-muted small">
            
          </span>
        </div>
      </nav>
      
      <main className="py-4">
        <ClubGrid clubs={clubs} />
      </main>
    </div>
  );
}

export default App;