import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    const fetchVersion = async () => {
      try {
        const response = await axios.get('/api/dashboard/version');
        setVersion(response.data.version);
      } catch (error) {
        console.error('Failed to fetch version:', error);
      }
    };
    fetchVersion();
  }, []);

  return (
    <footer className="footer">
      <div className="footer-content">
        <p>
          Copyright © {currentYear} TU Delft - Research & Education IT (REIT)
          {version && ` • v${version}`}
        </p>
        <p className="footer-links">
          <a
            href="https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitLab Repository
          </a>
          {' • '}
          <a
            href={`${import.meta.env.VITE_API_URL || ''}/docs`}
            target="_blank"
            rel="noopener noreferrer"
          >
            API Documentation
          </a>
        </p>
      </div>
    </footer>
  );
};

export default Footer;
