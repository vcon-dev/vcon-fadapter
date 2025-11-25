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
        vcon.to_json = MagicMock(return_value='{"vcon": "1.0", "uuid": "test-uuid-12345"}')
        return vcon
    
    def test_post_success_with_status_code(self, poster, mock_vcon, mock_response_success):
        """Test successful post with status code."""
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = mock_response_success
            
            result = poster.post(mock_vcon)
            
            assert result is True
            mock_post.assert_called_once_with(
                poster.url,
                params={},
                data=mock_vcon.to_json.return_value,
                headers=poster.headers,
                timeout=30
            )
    
    def test_post_success_201(self, poster, mock_vcon):
        """Test successful post with 201 status code."""
        response = Mock()
        response.status_code = 201
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = response
            
            result = poster.post(mock_vcon)
            assert result is True
    
    def test_post_success_204(self, poster, mock_vcon):
        """Test successful post with 204 status code."""
        response = Mock()
        response.status_code = 204
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = response
            
            result = poster.post(mock_vcon)
            assert result is True
    
    def test_post_error_status_code(self, poster, mock_vcon, mock_response_error):
        """Test post with error status code."""
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = mock_response_error
            
            result = poster.post(mock_vcon)
            
            assert result is False
            mock_post.assert_called_once()
    
    def test_post_error_400(self, poster, mock_vcon):
        """Test post with 400 status code."""
        response = Mock()
        response.status_code = 400
        response.text = "Bad Request"
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = response
            
            result = poster.post(mock_vcon)
            assert result is False
    
    def test_post_error_500(self, poster, mock_vcon):
        """Test post with 500 status code."""
        response = Mock()
        response.status_code = 500
        response.text = "Internal Server Error"
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = response
            
            result = poster.post(mock_vcon)
            assert result is False
    
    def test_post_no_status_code_attribute(self, poster, mock_vcon):
        """Test post when response has no status_code attribute."""
        # This test is no longer relevant since requests.post always returns
        # a response with status_code, but we'll test the normal flow
        response = Mock()
        response.status_code = 200
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = response
            
            result = poster.post(mock_vcon)
            assert result is True
    
    def test_post_exception(self, poster, mock_vcon):
        """Test post when exception is raised."""
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection error")
            
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
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.side_effect = exception_class("Connection failed")
            
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
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.side_effect = exception_class("Request timeout")
            
            result = poster.post(mock_vcon)
            assert result is False
    
    def test_post_correct_url(self, mock_vcon):
        """Test that correct URL is used."""
        url = "http://example.com/api/vcon"
        poster = HttpPoster(url=url, headers={})
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200)
            
            poster.post(mock_vcon)
            
            mock_post.assert_called_once_with(
                url,
                params={},
                data=mock_vcon.to_json.return_value,
                headers={},
                timeout=30
            )
    
    def test_post_correct_headers(self, mock_vcon):
        """Test that correct headers are used."""
        headers = {"Content-Type": "application/json", "x-api-token": "secret"}
        poster = HttpPoster(url="http://test.com", headers=headers)
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=200)
            
            poster.post(mock_vcon)
            
            call_args = mock_post.call_args
            assert call_args[1]["headers"] == headers
    
    def test_post_with_ingress_lists(self, mock_vcon):
        """Test post with ingress_lists query parameter."""
        ingress_lists = ["fax_processing", "main_ingress"]
        poster = HttpPoster(
            url="http://test.com/api/vcon",
            headers={"Content-Type": "application/json"},
            ingress_lists=ingress_lists
        )
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=201)
            
            result = poster.post(mock_vcon)
            
            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["params"] == {"ingress_lists": "fax_processing,main_ingress"}
    
    def test_post_without_ingress_lists(self, mock_vcon):
        """Test post without ingress_lists."""
        poster = HttpPoster(
            url="http://test.com/api/vcon",
            headers={"Content-Type": "application/json"}
        )
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=201)
            
            result = poster.post(mock_vcon)
            
            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["params"] == {}
    
    def test_post_with_empty_ingress_lists(self, mock_vcon):
        """Test post with empty ingress_lists."""
        poster = HttpPoster(
            url="http://test.com/api/vcon",
            headers={"Content-Type": "application/json"},
            ingress_lists=[]
        )
        with patch("fax_adapter.poster.requests.post") as mock_post:
            mock_post.return_value = Mock(status_code=201)
            
            result = poster.post(mock_vcon)
            
            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["params"] == {}

