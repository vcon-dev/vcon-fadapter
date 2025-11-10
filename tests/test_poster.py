"""Tests for poster.py module."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fax_adapter.poster import HttpPoster


class TestHttpPoster:
    """Test cases for HttpPoster class."""
    
    @pytest.fixture
    def poster(self):
        """Create an HttpPoster instance."""
        return HttpPoster(
            url="http://localhost:8000/api/vcon",
            headers={"Content-Type": "application/json", "x-api-token": "test-token"}
        )
    
    @pytest.fixture
    def mock_vcon(self):
        """Create a mock vCon object."""
        vcon = MagicMock()
        vcon.uuid = "test-uuid-12345"
        return vcon
    
    def test_post_success_with_status_code(self, poster, mock_vcon, mock_response_success):
        """Test successful post with status code."""
        mock_vcon.post_to_url.return_value = mock_response_success
        
        result = poster.post(mock_vcon)
        
        assert result is True
        mock_vcon.post_to_url.assert_called_once_with(
            poster.url,
            headers=poster.headers
        )
    
    def test_post_success_201(self, poster, mock_vcon):
        """Test successful post with 201 status code."""
        response = Mock()
        response.status_code = 201
        mock_vcon.post_to_url.return_value = response
        
        result = poster.post(mock_vcon)
        assert result is True
    
    def test_post_success_204(self, poster, mock_vcon):
        """Test successful post with 204 status code."""
        response = Mock()
        response.status_code = 204
        mock_vcon.post_to_url.return_value = response
        
        result = poster.post(mock_vcon)
        assert result is True
    
    def test_post_error_status_code(self, poster, mock_vcon, mock_response_error):
        """Test post with error status code."""
        mock_vcon.post_to_url.return_value = mock_response_error
        
        result = poster.post(mock_vcon)
        
        assert result is False
        mock_vcon.post_to_url.assert_called_once()
    
    def test_post_error_400(self, poster, mock_vcon):
        """Test post with 400 status code."""
        response = Mock()
        response.status_code = 400
        mock_vcon.post_to_url.return_value = response
        
        result = poster.post(mock_vcon)
        assert result is False
    
    def test_post_error_500(self, poster, mock_vcon):
        """Test post with 500 status code."""
        response = Mock()
        response.status_code = 500
        mock_vcon.post_to_url.return_value = response
        
        result = poster.post(mock_vcon)
        assert result is False
    
    def test_post_no_status_code_attribute(self, poster, mock_vcon):
        """Test post when response has no status_code attribute."""
        # Some implementations might return None or a different type
        mock_vcon.post_to_url.return_value = None
        
        result = poster.post(mock_vcon)
        
        # Should assume success if no exception and no status_code
        assert result is True
    
    def test_post_exception(self, poster, mock_vcon):
        """Test post when exception is raised."""
        mock_vcon.post_to_url.side_effect = Exception("Connection error")
        
        result = poster.post(mock_vcon)
        
        assert result is False
    
    def test_post_connection_error(self, poster, mock_vcon):
        """Test post with connection error."""
        try:
            import requests
            exception_class = requests.exceptions.ConnectionError
        except ImportError:
            # If requests is not available, use generic Exception
            exception_class = Exception
        mock_vcon.post_to_url.side_effect = exception_class("Connection failed")
        
        result = poster.post(mock_vcon)
        assert result is False
    
    def test_post_timeout_error(self, poster, mock_vcon):
        """Test post with timeout error."""
        try:
            import requests
            exception_class = requests.exceptions.Timeout
        except ImportError:
            # If requests is not available, use generic Exception
            exception_class = Exception
        mock_vcon.post_to_url.side_effect = exception_class("Request timeout")
        
        result = poster.post(mock_vcon)
        assert result is False
    
    def test_post_correct_url(self, mock_vcon):
        """Test that correct URL is used."""
        url = "http://example.com/api/vcon"
        poster = HttpPoster(url=url, headers={})
        mock_vcon.post_to_url.return_value = Mock(status_code=200)
        
        poster.post(mock_vcon)
        
        mock_vcon.post_to_url.assert_called_once_with(url, headers={})
    
    def test_post_correct_headers(self, mock_vcon):
        """Test that correct headers are used."""
        headers = {"Content-Type": "application/json", "x-api-token": "secret"}
        poster = HttpPoster(url="http://test.com", headers=headers)
        mock_vcon.post_to_url.return_value = Mock(status_code=200)
        
        poster.post(mock_vcon)
        
        call_args = mock_vcon.post_to_url.call_args
        assert call_args[1]["headers"] == headers

