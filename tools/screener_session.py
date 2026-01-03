"""
Screener.in session management using requests + BeautifulSoup.
Much simpler and more compatible than Playwright.
"""

import os
import pickle
from pathlib import Path
from typing import Optional, Dict, List
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


class ScreenerSession:
    """Manages authenticated sessions with screener.in using requests"""

    def __init__(self):
        load_dotenv()
        self.email = os.getenv('SCREENER_EMAIL')
        self.password = os.getenv('SCREENER_PASSWORD')

        if not self.email or not self.password:
            raise ValueError(
                "SCREENER_EMAIL and SCREENER_PASSWORD must be set in .env file. "
                "Copy .env.example to .env and fill in your credentials."
            )

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        self.cookies_file = Path('.playwright-mcp') / 'cookies.pkl'
        self.logged_in = False

    def start(self):
        """Start session and login if needed"""
        # Try to load existing cookies
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, 'rb') as f:
                    self.session.cookies.update(pickle.load(f))

                # Test if session is still valid
                response = self.session.get('https://www.screener.in/dash/')
                if response.url.startswith('https://www.screener.in/dash/'):
                    print("Using existing authenticated session")
                    self.logged_in = True
                    return
            except Exception as e:
                print(f"Could not restore session: {e}")

        # Need to login
        self._login()

    def _login(self):
        """Perform login to screener.in"""
        print("Logging into screener.in...")

        try:
            # Get login page to get CSRF token
            login_page = self.session.get('https://www.screener.in/login/')
            soup = BeautifulSoup(login_page.content, 'html.parser')

            # Find CSRF token
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            if not csrf_token:
                raise Exception("Could not find CSRF token")

            # Prepare login data
            login_data = {
                'csrfmiddlewaretoken': csrf_token['value'],
                'username': self.email,
                'password': self.password,
            }

            # Perform login
            response = self.session.post(
                'https://www.screener.in/login/',
                data=login_data,
                headers={'Referer': 'https://www.screener.in/login/'}
            )

            # Check if login was successful
            if response.url.startswith('https://www.screener.in/dash/'):
                print("Login successful")
                self.logged_in = True

                # Save cookies
                self.cookies_file.parent.mkdir(exist_ok=True)
                with open(self.cookies_file, 'wb') as f:
                    pickle.dump(self.session.cookies, f)
            else:
                raise Exception(f"Login failed. Redirected to: {response.url}")

        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")

    def navigate(self, url: str) -> str:
        """Navigate to a URL and return the HTML content"""
        if not self.logged_in:
            raise RuntimeError("Not logged in. Call start() first.")

        response = self.session.get(url)
        response.raise_for_status()
        return response.text

    def navigate_all_pages(self, base_url: str, max_pages: int = 0, page_delay: float = 1.5, verbose: bool = True) -> Dict:
        """
        Navigate through all pages of results and collect data from each page.

        Args:
            base_url: The base URL (without page parameter)
            max_pages: Maximum number of pages to fetch (0 = unlimited)
            page_delay: Delay in seconds between page requests (for rate limiting)
            verbose: Print progress information

        Returns:
            Dictionary with:
            - all_stocks: Combined list of all stocks from all pages
            - total_results: Total number of results
            - pages_fetched: Number of pages actually fetched
            - headers: Column headers
        """
        import time

        if not self.logged_in:
            raise RuntimeError("Not logged in. Call start() first.")

        all_stocks = []
        headers = []
        total_results = 0
        pages_fetched = 0

        # Fetch first page to get pagination info
        if verbose:
            print(f"\n[PAGINATION] Fetching page 1...")

        html = self.navigate(base_url)
        table_data = self.extract_table_data(html)

        if not table_data or 'rows' not in table_data:
            return {
                'all_stocks': [],
                'total_results': 0,
                'pages_fetched': 0,
                'headers': []
            }

        # Store first page data
        headers = table_data['headers']
        all_stocks.extend(table_data['rows'])
        pages_fetched = 1

        pagination = table_data.get('pagination', {})
        total_pages = pagination.get('total_pages', 1)
        total_results = pagination.get('total_results', len(all_stocks))

        if verbose:
            print(f"[PAGINATION] Found {total_results} total results across {total_pages} pages")
            print(f"[PAGINATION] Page 1/{total_pages}: Collected {len(table_data['rows'])} stocks")

        # Determine how many pages to fetch
        pages_to_fetch = total_pages
        if max_pages > 0:
            pages_to_fetch = min(total_pages, max_pages)

        # Fetch remaining pages
        for page_num in range(2, pages_to_fetch + 1):
            # Add delay to avoid rate limiting
            time.sleep(page_delay)

            # Build URL with page parameter
            page_url = f"{base_url}&page={page_num}" if '?' in base_url else f"{base_url}?page={page_num}"

            if verbose:
                print(f"[PAGINATION] Fetching page {page_num}/{pages_to_fetch}...")

            try:
                html = self.navigate(page_url)
                table_data = self.extract_table_data(html)

                if table_data and 'rows' in table_data and table_data['rows']:
                    all_stocks.extend(table_data['rows'])
                    pages_fetched += 1

                    if verbose:
                        print(f"[PAGINATION] Page {page_num}/{pages_to_fetch}: Collected {len(table_data['rows'])} stocks")
                else:
                    if verbose:
                        print(f"[PAGINATION] Page {page_num}/{pages_to_fetch}: No data found")
                    break

            except Exception as e:
                if verbose:
                    print(f"[PAGINATION] Error fetching page {page_num}: {e}")
                break

        if verbose:
            print(f"\n[PAGINATION] Complete! Fetched {pages_fetched} pages, collected {len(all_stocks)} stocks total")

        return {
            'all_stocks': all_stocks,
            'total_results': total_results,
            'pages_fetched': pages_fetched,
            'headers': headers
        }

    def extract_table_data(self, html: str) -> Dict:
        """
        Extract table data from HTML.
        Returns a dictionary with headers, rows, and pagination info.
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Find the table
        table = soup.find('table')
        if not table:
            return {'headers': [], 'rows': [], 'pagination': {'has_next': False, 'current_page': 1, 'total_pages': 1}}

        # Extract headers - preserve whitespace in column names
        headers = []
        header_row = table.find('thead')
        if header_row:
            headers = [' '.join(th.get_text().split()) for th in header_row.find_all('th')]
        else:
            # Fallback: first row might be headers
            first_row = table.find('tbody').find('tr')
            if first_row:
                headers = [' '.join(th.get_text().split()) for th in first_row.find_all('th')]

        # Extract data rows
        rows = []
        tbody = table.find('tbody')
        if tbody:
            data_rows = tbody.find_all('tr')[1:]  # Skip header row if it's in tbody

            for row in data_rows:
                cells = row.find_all('td')
                if not cells:  # Skip empty rows
                    continue

                # Extract data-row-company-id from <tr> tag
                company_id = row.get('data-row-company-id')

                row_data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        value = ' '.join(cell.get_text().split())
                        row_data[headers[i]] = value if value else None

                        # Extract company href for backward compatibility
                        # The company name cell contains an <a> tag with href="/company/SYMBOL/"
                        # This is typically in the "Name" column (first or second column)
                        if i < 3:  # Check first 3 columns for company link
                            link = cell.find('a')
                            if link and link.has_attr('href'):
                                href = link.get('href')
                                # Store href for later enrichment (internal field)
                                if '/company/' in href:
                                    row_data['_company_href'] = href

                # Add company ID to row data
                if company_id:
                    row_data['_company_id'] = company_id

                rows.append(row_data)

        # Extract pagination info
        pagination = self._extract_pagination_info(soup)

        return {'headers': headers, 'rows': rows, 'pagination': pagination}

    def _extract_pagination_info(self, soup: BeautifulSoup) -> Dict:
        """
        Extract pagination information from the page.

        Returns:
            Dictionary with pagination info:
            - has_next: Whether there's a next page
            - current_page: Current page number
            - total_pages: Total number of pages (if available)
            - total_results: Total number of results
        """
        # Screener.in shows pagination info in: <div class="sub" data-page-info="">
        # Format: "169 results found: Showing page 1 of 4"

        # First try: Find div with class 'sub' and has attribute 'data-page-info'
        page_info_div = soup.find('div', class_='sub', attrs={'data-page-info': True})

        # If not found, search all divs with class 'sub' for the pattern
        if not page_info_div:
            sub_divs = soup.find_all('div', class_='sub')
            for div in sub_divs:
                text = div.get_text().strip()
                if 'results found' in text and 'Showing page' in text:
                    page_info_div = div
                    break

        if not page_info_div:
            # No pagination found - single page
            return {
                'has_next': False,
                'current_page': 1,
                'total_pages': 1,
                'total_results': 0
            }

        # Parse the text: "169 results found: Showing page 1 of 4"
        info_text = page_info_div.get_text().strip()

        total_results = 0
        current_page = 1
        total_pages = 1

        # Extract total results
        if 'results found' in info_text:
            try:
                # Extract number before "results found"
                results_part = info_text.split('results found')[0].strip()
                total_results = int(results_part)
            except (ValueError, IndexError):
                pass

        # Extract current page and total pages
        if 'Showing page' in info_text and 'of' in info_text:
            try:
                # Extract "page X of Y"
                page_part = info_text.split('Showing page')[1].strip()
                parts = page_part.split('of')
                current_page = int(parts[0].strip())
                total_pages = int(parts[1].strip())
            except (ValueError, IndexError):
                pass

        has_next = current_page < total_pages

        return {
            'has_next': has_next,
            'current_page': current_page,
            'total_pages': total_pages,
            'total_results': total_results
        }

    def get_configured_columns(self) -> List[str]:
        """
        Get the list of currently configured columns from user's profile.

        Returns:
            List of column names that are currently enabled
        """
        if not self.logged_in:
            raise RuntimeError("Not logged in. Call start() first.")

        response = self.session.get('https://www.screener.in/user/columns/')
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the columns form (second form on the page)
        forms = soup.find_all('form')
        if len(forms) < 2:
            raise RuntimeError("Could not find columns form")

        columns_form = forms[1]

        # Find the hidden 'data' input that contains current columns
        data_input = columns_form.find('input', {'name': 'data'})
        if not data_input:
            return []

        current_columns_str = data_input.get('value', '')
        if not current_columns_str:
            return []

        # Split by comma to get list of columns
        columns = [col.strip() for col in current_columns_str.split(',') if col.strip()]
        return columns

    def get_available_columns(self) -> Dict[str, str]:
        """
        Get all available columns that can be configured.

        Returns:
            Dictionary mapping column names to their descriptions
        """
        if not self.logged_in:
            raise RuntimeError("Not logged in. Call start() first.")

        response = self.session.get('https://www.screener.in/user/columns/')
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all ratio labels
        ratio_labels = soup.find_all('label', class_='ratio')

        available_columns = {}
        for label in ratio_labels:
            data_name = label.get('data-name')
            description = label.get('data-description', '')
            if data_name:
                available_columns[data_name] = description

        return available_columns

    def configure_columns(self, columns: List[str], next_url: Optional[str] = None) -> bool:
        """
        Configure which columns should appear in query results.
        This updates the user's column preferences on screener.in.

        Args:
            columns: List of column names to enable
            next_url: Optional URL to redirect to after saving (used by screener.in)

        Returns:
            True if successful, False otherwise
        """
        if not self.logged_in:
            raise RuntimeError("Not logged in. Call start() first.")

        # First, get the CSRF token
        response = self.session.get('https://www.screener.in/user/columns/')
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the columns form
        forms = soup.find_all('form')
        if len(forms) < 2:
            raise RuntimeError("Could not find columns form")

        columns_form = forms[1]

        # Get CSRF token
        csrf_input = columns_form.find('input', {'name': 'csrfmiddlewaretoken'})
        if not csrf_input:
            raise RuntimeError("Could not find CSRF token")

        csrf_token = csrf_input.get('value')

        # Prepare form data
        # The 'data' field should contain comma-separated column names
        form_data = {
            'csrfmiddlewaretoken': csrf_token,
            'data': ','.join(columns)
        }

        # Submit the form
        url = 'https://www.screener.in/user/columns/'
        if next_url:
            url += f'?next={next_url}'

        response = self.session.post(
            url,
            data=form_data,
            headers={'Referer': 'https://www.screener.in/user/columns/'}
        )

        # Check if successful (should redirect or return success)
        if response.status_code == 200 or response.status_code == 302:
            print(f"Successfully configured {len(columns)} columns")
            return True
        else:
            print(f"Failed to configure columns. Status: {response.status_code}")
            return False

    def close(self):
        """Close session"""
        self.session.close()

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
