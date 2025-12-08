"""
Rate Limiting for Jira MCP Server

Simple in-memory rate limiter to protect against abuse.
Can be upgraded to Redis-based for production distributed deployments.
"""

import time
from functools import wraps
from typing import Dict, Tuple, Callable, Any
from flask import request, jsonify
import threading


class RateLimiter:
    """
    Token bucket rate limiter implementation.

    Tracks requests per IP address and enforces limits.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        cleanup_interval: int = 300
    ):
        """
        Initialize the rate limiter.

        Args:
            requests_per_minute: Max requests allowed per minute per IP
            requests_per_hour: Max requests allowed per hour per IP
            cleanup_interval: How often to clean up old entries (seconds)
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.cleanup_interval = cleanup_interval

        # Storage: {ip: [(timestamp, count), ...]}
        self._minute_buckets: Dict[str, list] = {}
        self._hour_buckets: Dict[str, list] = {}

        # Thread safety
        self._lock = threading.Lock()

        # Last cleanup time
        self._last_cleanup = time.time()

    def _get_client_ip(self) -> str:
        """Get the client IP address from the request."""
        # Check for forwarded headers (common in reverse proxy setups)
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        if request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr or 'unknown'

    def _cleanup_old_entries(self):
        """Remove expired entries from the buckets."""
        current_time = time.time()

        # Only cleanup periodically
        if current_time - self._last_cleanup < self.cleanup_interval:
            return

        with self._lock:
            self._last_cleanup = current_time
            minute_ago = current_time - 60
            hour_ago = current_time - 3600

            # Clean minute buckets
            for ip in list(self._minute_buckets.keys()):
                self._minute_buckets[ip] = [
                    (ts, count) for ts, count in self._minute_buckets[ip]
                    if ts > minute_ago
                ]
                if not self._minute_buckets[ip]:
                    del self._minute_buckets[ip]

            # Clean hour buckets
            for ip in list(self._hour_buckets.keys()):
                self._hour_buckets[ip] = [
                    (ts, count) for ts, count in self._hour_buckets[ip]
                    if ts > hour_ago
                ]
                if not self._hour_buckets[ip]:
                    del self._hour_buckets[ip]

    def _count_requests(self, ip: str, window_seconds: int, buckets: Dict) -> int:
        """Count requests for an IP within a time window."""
        current_time = time.time()
        cutoff = current_time - window_seconds

        if ip not in buckets:
            return 0

        return sum(
            count for ts, count in buckets[ip]
            if ts > cutoff
        )

    def _record_request(self, ip: str):
        """Record a new request for an IP."""
        current_time = time.time()

        with self._lock:
            # Record in minute bucket
            if ip not in self._minute_buckets:
                self._minute_buckets[ip] = []
            self._minute_buckets[ip].append((current_time, 1))

            # Record in hour bucket
            if ip not in self._hour_buckets:
                self._hour_buckets[ip] = []
            self._hour_buckets[ip].append((current_time, 1))

    def is_allowed(self, ip: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed under rate limits.

        Args:
            ip: Optional IP address (defaults to current request IP)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        self._cleanup_old_entries()

        if ip is None:
            ip = self._get_client_ip()

        with self._lock:
            minute_count = self._count_requests(ip, 60, self._minute_buckets)
            hour_count = self._count_requests(ip, 3600, self._hour_buckets)

        info = {
            'ip': ip,
            'minute_count': minute_count,
            'minute_limit': self.requests_per_minute,
            'minute_remaining': max(0, self.requests_per_minute - minute_count),
            'hour_count': hour_count,
            'hour_limit': self.requests_per_hour,
            'hour_remaining': max(0, self.requests_per_hour - hour_count),
        }

        # Check minute limit
        if minute_count >= self.requests_per_minute:
            info['retry_after'] = 60
            info['limit_type'] = 'minute'
            return False, info

        # Check hour limit
        if hour_count >= self.requests_per_hour:
            info['retry_after'] = 3600
            info['limit_type'] = 'hour'
            return False, info

        # Request is allowed, record it
        self._record_request(ip)

        return True, info

    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics."""
        with self._lock:
            return {
                'tracked_ips_minute': len(self._minute_buckets),
                'tracked_ips_hour': len(self._hour_buckets),
                'limits': {
                    'per_minute': self.requests_per_minute,
                    'per_hour': self.requests_per_hour,
                }
            }


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=60,  # 1 request per second average
    requests_per_hour=1000,  # ~16 requests per minute average
)


def rate_limit(func: Callable) -> Callable:
    """
    Decorator to apply rate limiting to a Flask route.

    Usage:
        @app.route('/api/endpoint')
        @rate_limit
        def endpoint():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        is_allowed, info = rate_limiter.is_allowed()

        if not is_allowed:
            response = jsonify({
                'jsonrpc': '2.0',
                'id': None,
                'error': {
                    'code': -32000,
                    'message': f'Rate limit exceeded. Try again in {info["retry_after"]} seconds.',
                    'data': {
                        'limit_type': info['limit_type'],
                        'retry_after': info['retry_after']
                    }
                }
            })
            response.status_code = 429
            response.headers['Retry-After'] = str(info['retry_after'])
            response.headers['X-RateLimit-Limit-Minute'] = str(info['minute_limit'])
            response.headers['X-RateLimit-Remaining-Minute'] = str(info['minute_remaining'])
            response.headers['X-RateLimit-Limit-Hour'] = str(info['hour_limit'])
            response.headers['X-RateLimit-Remaining-Hour'] = str(info['hour_remaining'])
            return response

        # Add rate limit headers to successful responses
        result = func(*args, **kwargs)

        # If result is a tuple (response, status_code), handle it
        if isinstance(result, tuple):
            response, status_code = result[0], result[1] if len(result) > 1 else 200
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit-Minute'] = str(info['minute_limit'])
                response.headers['X-RateLimit-Remaining-Minute'] = str(info['minute_remaining'])
            return result

        # If result has headers attribute (is a Response object)
        if hasattr(result, 'headers'):
            result.headers['X-RateLimit-Limit-Minute'] = str(info['minute_limit'])
            result.headers['X-RateLimit-Remaining-Minute'] = str(info['minute_remaining'])

        return result

    return wrapper


def check_rate_limit() -> Tuple[bool, Dict[str, Any]]:
    """
    Check rate limit without recording a request.
    Useful for preflight checks.

    Returns:
        Tuple of (is_allowed, rate_limit_info)
    """
    ip = rate_limiter._get_client_ip()

    with rate_limiter._lock:
        minute_count = rate_limiter._count_requests(ip, 60, rate_limiter._minute_buckets)
        hour_count = rate_limiter._count_requests(ip, 3600, rate_limiter._hour_buckets)

    return (
        minute_count < rate_limiter.requests_per_minute and
        hour_count < rate_limiter.requests_per_hour
    ), {
        'minute_remaining': max(0, rate_limiter.requests_per_minute - minute_count),
        'hour_remaining': max(0, rate_limiter.requests_per_hour - hour_count),
    }
