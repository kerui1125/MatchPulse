"""
Configuration and utility tests that don't require external dependencies.

Run with: pytest tests/test_config.py -v
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from src.tools.utils import load_config, get_company_links


class TestConfiguration:
    """Test configuration loading and validation."""
    
    def test_load_config_exists(self):
        """Test that config file can be loaded."""
        config = load_config()
        assert config is not None, "Config should not be None"
        assert isinstance(config, dict), "Config should be a dictionary"
    
    def test_config_has_links(self):
        """Test that config contains company links."""
        config = load_config()
        assert 'links' in config, "Config should have 'links' section"
        assert isinstance(config['links'], dict), "'links' should be a dictionary"
    
    def test_get_company_links_returns_dict(self):
        """Test that get_company_links returns a dictionary."""
        links = get_company_links()
        assert isinstance(links, dict), "Should return a dictionary"
    
    def test_company_links_not_empty(self):
        """Test that there are company links configured."""
        links = get_company_links()
        assert len(links) > 0, "Should have at least one company configured"
    
    def test_company_links_valid_urls(self):
        """Test that all company links are valid URLs."""
        links = get_company_links()
        
        for company, url in links.items():
            assert isinstance(url, str), f"{company} URL should be a string"
            assert url.startswith('http'), f"{company} URL should start with http/https"
            assert len(url) > 10, f"{company} URL seems too short: {url}"
    
    def test_expected_companies_present(self):
        """Test that expected companies are in config."""
        links = get_company_links()
        
        # Check for at least some of the 7 companies
        expected_companies = ['amazon', 'google', 'microsoft', 'nvidia']
        
        # Convert to lowercase for case-insensitive comparison
        company_names_lower = [name.lower() for name in links.keys()]
        
        found_count = sum(1 for company in expected_companies if company in company_names_lower)
        assert found_count >= 3, f"Should have at least 3 of the expected companies, found {found_count}"


class TestEnvironmentSetup:
    """Test that required directories and environment are set up."""
    
    def test_data_directory_exists(self):
        """Test that data directory exists."""
        assert os.path.exists('data'), "data/ directory should exist"
    
    def test_src_directory_exists(self):
        """Test that src directory exists."""
        assert os.path.exists('src'), "src/ directory should exist"
    
    def test_config_file_exists(self):
        """Test that config file exists."""
        assert os.path.exists('src/config/config.yaml'), "config.yaml should exist"
    
    def test_agents_directory_exists(self):
        """Test that agents directory exists."""
        assert os.path.exists('src/agents'), "src/agents/ directory should exist"
    
    def test_tools_directory_exists(self):
        """Test that tools directory exists."""
        assert os.path.exists('src/tools'), "src/tools/ directory should exist"


# Run tests with: pytest tests/test_config.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
