"""Cookie Manager - Extracts cookies from browsers for authentication"""

import browser_cookie3
import tempfile
import os
from typing import Optional, Dict
from http.cookiejar import Cookie


class CookieManager:
    """Manages cookie extraction from browsers"""

    def __init__(self):
        self.cookies = {}  # Cached cookies by domain
        self.cookie_jar = None  # Full cookie jar
        self.load_cookies()

    def load_cookies(self, force_refresh=False):
        """
        Load cookies from all available browsers

        Args:
            force_refresh: If True, bypass cache and reload from browsers
        """
        if not force_refresh and self.cookies:
            return  # Use cached cookies

        self.cookies = {}
        self.cookie_jar = None

        try:
            # Try loading from all browsers at once
            self.cookie_jar = browser_cookie3.load()
            self._organize_cookies()
            return
        except Exception as e:
            print(f"Warning: Could not load cookies from all browsers: {e}")

        # Fallback: Try individual browsers
        browsers = [
            ('Chrome', browser_cookie3.chrome),
            ('Firefox', browser_cookie3.firefox),
            ('Edge', browser_cookie3.edge),
            ('Safari', browser_cookie3.safari),
            ('Brave', browser_cookie3.brave),
            ('Opera', browser_cookie3.opera),
            ('Opera GX', browser_cookie3.opera_gx),
            ('Vivaldi', browser_cookie3.vivaldi),
            ('Chromium', browser_cookie3.chromium),
        ]

        for browser_name, browser_func in browsers:
            try:
                jar = browser_func()
                if jar:
                    self.cookie_jar = jar
                    self._organize_cookies()
                    print(f"Successfully loaded cookies from {browser_name}")
                    return
            except Exception as e:
                # Silently try next browser
                continue

        print("Warning: Could not load cookies from any browser")

    def _organize_cookies(self):
        """Organize cookies by domain for quick access"""
        if not self.cookie_jar:
            return

        for cookie in self.cookie_jar:
            domain = cookie.domain
            if domain not in self.cookies:
                self.cookies[domain] = []
            self.cookies[domain].append(cookie)

    def get_cookies_for_domain(self, domain):
        """
        Get cookies for a specific domain

        Args:
            domain: Domain string (e.g., '.youtube.com', '.instagram.com')

        Returns:
            List of cookies for the domain
        """
        cookies = []

        # Direct match
        if domain in self.cookies:
            cookies.extend(self.cookies[domain])

        # Check for subdomain matches
        for cookie_domain, cookie_list in self.cookies.items():
            if domain.endswith(cookie_domain) or cookie_domain.endswith(domain):
                cookies.extend(cookie_list)

        return cookies

    def cookies_to_netscape(self, domain, output_file=None):
        """
        Convert cookies for a domain to Netscape format file

        Args:
            domain: Domain to extract cookies for
            output_file: Optional file path. If None, creates temp file

        Returns:
            Path to the Netscape cookies file
        """
        cookies = self.get_cookies_for_domain(domain)

        if not cookies:
            return None

        if output_file is None:
            # Create temporary file
            fd, output_file = tempfile.mkstemp(suffix='.txt', prefix='cookies_')
            os.close(fd)

        with open(output_file, 'w') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# This is a generated file! Do not edit.\n\n")

            for cookie in cookies:
                # Netscape format: domain, domain_specified, path, secure, expiration, name, value
                domain_specified = "TRUE" if cookie.domain.startswith('.') else "FALSE"
                secure = "TRUE" if cookie.secure else "FALSE"
                expiration = str(cookie.expires) if cookie.expires else "0"

                line = '\t'.join([
                    cookie.domain,
                    domain_specified,
                    cookie.path or '/',
                    secure,
                    expiration,
                    cookie.name,
                    cookie.value or ''
                ])
                f.write(line + '\n')

        return output_file

    def refresh_cookies(self):
        """Manually refresh cookies from browsers"""
        self.cookies = {}
        self.cookie_jar = None
        self.load_cookies(force_refresh=True)
        return bool(self.cookie_jar)

    def get_cookie_jar(self):
        """Get the full cookie jar"""
        return self.cookie_jar

    def has_cookies(self):
        """Check if any cookies were loaded"""
        return bool(self.cookies)
