import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { clubsApi } from './services/api';
import ClubGrid from './components/ClubGrid';
import ClubDetail from './components/ClubDetail';
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

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center min-vh-100">
        <div className="spinner-border text-light" role="status">
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
    <Router>
      <div className="min-vh-100">
        <nav className="dark-nav">
          <div className="container-fluid px-4 py-3">
            <span className="navbar-brand mb-0 h1 fw-bold" style={{ fontFamily: 'var(--font-jet)' }}>
              ledger 
            </span>
          </div>
        </nav>
        
        <main className="py-4">
          <Routes>
            <Route path="/" element={<ClubGrid clubs={clubs} />} />
            <Route path="/club/:clubName" element={<ClubDetail />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;