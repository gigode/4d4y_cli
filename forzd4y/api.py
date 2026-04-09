# -*- coding: utf-8 -*-
"""
API client for 4d4y forum.
Handles HTTP requests, session management, and forum interactions.
"""

import re
import hashlib
import time
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from .config import Config


class ApiError(Exception):
    """API-related errors."""
    pass


class ForumApi:
    """Main API client for interacting with 4d4y forum."""

    # HTTP headers mimicking a browser
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Login form field names
    LOGIN_SUCCESS_MARKER = "欢迎您"
    LOGIN_FAIL_MARKER = "密码错误"

    def __init__(self, config=None):
        """
        Initialize API client.

        Args:
            config: Config instance for credentials and session
        """
        self.config = config or Config()
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self._formhash = None

        # Try to restore session from saved cookies
        self._restore_session()

    def _restore_session(self):
        """Attempt to restore session from saved cookies."""
        saved_cookies = self.config.load_cookies()
        if saved_cookies:
            for name, value in saved_cookies.items():
                self.session.cookies.set(name, value)

    def _save_cookies(self):
        """Persist cookies to config for session restoration."""
        cookies_dict = {k: v for k, v in self.session.cookies.get_dict().items()}
        self.config.save_cookies(cookies_dict)

    def get(self, url, params=None, **kwargs):
        """
        Perform GET request.

        Args:
            url: Target URL
            params: Query parameters
            **kwargs: Additional arguments passed to requests

        Returns:
            Response text content
        """
        try:
            response = self.session.get(url, params=params, **kwargs)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise ApiError(f"GET request failed: {e}")

    def post(self, url, data=None, **kwargs):
        """
        Perform POST request.

        Args:
            url: Target URL
            data: Form data
            **kwargs: Additional arguments passed to requests

        Returns:
            Response text content
        """
        try:
            response = self.session.post(url, data=data, **kwargs)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise ApiError(f"POST request failed: {e}")

    def _extract_formhash(self, html_content):
        """
        Extract formhash from HTML content.

        Args:
            html_content: HTML page text

        Returns:
            Formhash string or None if not found
        """
        # Pattern to match formhash value in hidden input fields
        patterns = [
            r'name="formhash"[^>]*value="([^"]+)"',
            r'formhash=([a-f0-9]{8})',
        ]
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)
        return None

    def get_formhash(self):
        """
        Fetch login page and extract formhash.

        Returns:
            Formhash string

        Raises:
            ApiError: If formhash cannot be extracted
        """
        url = urljoin(self.config.BASE_URL, "logging.php?action=login")
        html = self.get(url)

        formhash = self._extract_formhash(html)
        if not formhash:
            raise ApiError("无法获取登录凭据 (formhash)")
        return formhash

    def login(self, username=None, password=None):
        """
        Authenticate with the forum.

        Args:
            username: Forum username (uses config if not provided)
            password: Forum password (uses config if not provided)

        Returns:
            True if login successful

        Raises:
            ApiError: If login fails
        """
        username = username or self.config.username
        password = password or self.config.password

        if not username or not password:
            raise ApiError("用户名和密码不能为空")

        # Get fresh formhash
        formhash = self.get_formhash()

        # Prepare login data
        login_url = urljoin(self.config.BASE_URL, "logging.php?action=login&loginsubmit=yes&inajax=1")

        # Process password (Discuz uses MD5)
        processed_password = self._process_password(password)

        post_data = {
            "m_formhash": formhash,
            "referer": self.config.BASE_URL + "index.php",
            "loginfield": "username",
            "username": username,
            "password": processed_password,
            "questionid": "0",
            "answer": "",
            "cookietime": "2592000",
        }

        response = self.post(login_url, data=post_data)

        # Check login result
        if self.LOGIN_SUCCESS_MARKER in response:
            self.config.username = username
            self.config.password = password  # Store for potential re-login
            self.config.logged_in = True
            self.config.formhash = formhash
            self.config.save_config()
            self._save_cookies()

            # Extract uid from response if available
            uid_match = re.search(r'uid=(\d+)', response)
            if uid_match:
                self.config.uid = uid_match.group(1)

            return True
        elif self.LOGIN_FAIL_MARKER in response:
            raise ApiError("登录失败：用户名或密码错误")
        else:
            # Check if already logged in by looking for user info
            if self._check_logged_in():
                self.config.logged_in = True
                self.config.username = username
                self.config.save_config()
                self._save_cookies()
                return True
            raise ApiError("登录失败：未知错误")

    def _process_password(self, password):
        """
        Process password for Discuz login.
        Discuz uses MD5 hash of the password.

        Args:
            password: Plain text password

        Returns:
            MD5 hashed password
        """
        # If password is already 32 chars (MD5), return as-is
        if len(password) == 32 and re.match(r'^[a-f0-9]{32}$', password):
            return password

        # Escape special characters and compute MD5
        escaped = password.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
        return hashlib.md5(escaped.encode('utf-8')).hexdigest()

    def _check_logged_in(self):
        """
        Check if current session is logged in.

        Returns:
            True if logged in, False otherwise
        """
        try:
            # Try to fetch home page and check for user menu
            html = self.get(self.config.BASE_URL + "index.php")
            return "space.php" in html or "logging.php" not in html
        except:
            return False

    def is_logged_in(self):
        """
        Check if user is logged in.

        Returns:
            True if logged in
        """
        return self.config.is_logged_in() and self._check_logged_in()

    def logout(self):
        """
        Log out from the forum.
        """
        try:
            logout_url = urljoin(self.config.BASE_URL, "logging.php?action=logout")
            self.get(logout_url)
        except:
            pass
        finally:
            self.config.logged_in = False
            self.config.username = ""
            self.config.password = ""
            self.config.uid = ""
            self.config.formhash = ""
            self.config.save_config()
            self.config.clear_cookies()
            self.session.cookies.clear()

    def get_forum_list(self, gid=None):
        """
        Get list of forums or sub-forums.

        Args:
            gid: Optional group ID to filter forums

        Returns:
            List of forum info dictionaries
        """
        url = urljoin(self.config.BASE_URL, "index.php")
        if gid:
            url += f"?gid={gid}"

        html = self.get(url)
        return self._parse_forum_list(html)

    def _parse_forum_list(self, html):
        """
        Parse forum list from HTML.

        Args:
            html: Index page HTML

        Returns:
            List of dicts with forum info
        """
        forums = []
        soup = BeautifulSoup(html, "html.parser")

        # Find forum list - typically in table or div structure
        # Look for forumdisplay links
        forum_links = soup.find_all("a", href=re.compile(r"forumdisplay\.php\?fid=\d+"))

        seen_fids = set()
        for link in forum_links:
            href = link.get("href", "")
            fid_match = re.search(r"fid=(\d+)", href)
            if fid_match:
                fid = int(fid_match.group(1))
                if fid not in seen_fids:
                    seen_fids.add(fid)
                    forums.append({
                        "fid": fid,
                        "name": link.get_text(strip=True),
                        "url": href,
                    })

        return forums

    def get_thread_list(self, fid, page=1):
        """
        Get thread list for a forum.

        Args:
            fid: Forum ID
            page: Page number (1-based)

        Returns:
            Tuple of (threads list, total pages, current page)
        """
        url = urljoin(self.config.BASE_URL, f"forumdisplay.php?fid={fid}&page={page}")
        html = self.get(url)
        return self._parse_thread_list(html, fid, page)

    def _parse_thread_list(self, html, fid, page):
        """
        Parse thread list from forum page.

        Args:
            html: Forum page HTML
            fid: Forum ID
            page: Current page number

        Returns:
            Tuple of (threads list, total pages, current page)
        """
        threads = []
        soup = BeautifulSoup(html, "html.parser")

        # Find pagination for total pages
        total_pages = 1
        pagination = soup.find("div", class_="pg")
        if pagination:
            page_links = pagination.find_all("a")
            for link in page_links:
                text = link.get_text(strip=True)
                if text.isdigit():
                    total_pages = max(total_pages, int(text))
            # Check current page info
            current = pagination.find("span", class_="xyz")  # Sometimes present
            if not current:
                # Try to find "Page 1 of X" pattern
                page_info = pagination.get_text()
                page_match = re.search(r"(\d+)/(\d+)", page_info)
                if page_match:
                    total_pages = int(page_match.group(2))

        # Find thread list - typically in tbody or table
        thread_rows = soup.find_all("tbody", id=re.compile(r"^normalthread_"))

        if not thread_rows:
            # Alternative: find all rows with thread links
            all_rows = soup.find_all("tr", class_=re.compile(r"thread"))
            for row in all_rows:
                thread_info = self._extract_thread_info(row)
                if thread_info:
                    threads.append(thread_info)
        else:
            for row in thread_rows:
                thread_info = self._extract_thread_info(row)
                if thread_info:
                    threads.append(thread_info)

        return threads, total_pages, page

    def _extract_thread_info(self, row):
        """
        Extract thread information from a table row.

        Args:
            row: BeautifulSoup element representing thread row

        Returns:
            Dictionary with thread info or None
        """
        try:
            # Find thread title link
            title_link = row.find("a", class_="s xst")
            if not title_link:
                title_link = row.find("a", href=re.compile(r"viewthread\.php\?tid=\d+"))

            if not title_link:
                return None

            href = title_link.get("href", "")
            tid_match = re.search(r"tid=(\d+)", href)
            tid = int(tid_match.group(1)) if tid_match else 0

            # Extract author
            author_link = row.find("a", href=re.compile(r"space\.php\?username="))
            author = author_link.get_text(strip=True) if author_link else "匿名"

            # Extract reply count and view count
            reply_count = 0
            view_count = 0
            stats = row.find_all("td", class_="num")
            if len(stats) >= 2:
                reply_text = stats[0].get_text(strip=True)
                view_text = stats[1].get_text(strip=True)
                reply_count = int(reply_text) if reply_text.isdigit() else 0
                view_count = int(view_text) if view_text.isdigit() else 0

            # Extract last post info
            last_post = ""
            last_post_time = ""
            last_post_link = row.find("a", class_="nobname")
            if last_post_link:
                last_post = last_post_link.get_text(strip=True)

            # Extract thread title
            title = title_link.get_text(strip=True)

            return {
                "tid": tid,
                "title": title,
                "author": author,
                "reply_count": reply_count,
                "view_count": view_count,
                "last_post": last_post,
                "url": href,
            }
        except Exception:
            return None

    def get_thread_detail(self, tid, page=1):
        """
        Get posts in a thread.

        Args:
            tid: Thread ID
            page: Page number

        Returns:
            Tuple of (posts list, total pages, current page, thread title)
        """
        url = urljoin(self.config.BASE_URL, f"viewthread.php?tid={tid}&page={page}")
        html = self.get(url)
        return self._parse_thread_detail(html, tid, page)

    def _parse_thread_detail(self, html, tid, page):
        """
        Parse thread detail page.

        Args:
            html: Thread page HTML
            tid: Thread ID
            page: Current page

        Returns:
            Tuple of (posts list, total pages, current page, thread title)
        """
        posts = []
        soup = BeautifulSoup(html, "html.parser")

        # Get thread title
        thread_title = "未知主题"
        title_elem = soup.find("span", id="threadtitle")
        if title_elem:
            thread_title = title_elem.get_text(strip=True)
        else:
            h1 = soup.find("h1")
            if h1:
                thread_title = h1.get_text(strip=True)

        # Find total pages
        total_pages = 1
        pagination = soup.find("div", class_="pg")
        if pagination:
            page_match = re.search(r"(\d+)/(\d+)", pagination.get_text())
            if page_match:
                total_pages = int(page_match.group(2))

        # Find all posts
        post_containers = soup.find_all("div", id=re.compile(r"^post_\d+$"))

        for container in post_containers:
            post = self._extract_post_info(container)
            if post:
                posts.append(post)

        return posts, total_pages, page, thread_title

    def _extract_post_info(self, container):
        """
        Extract post information from post container.

        Args:
            container: BeautifulSoup element for post

        Returns:
            Dictionary with post info
        """
        try:
            # Extract post ID
            post_id_match = re.search(r"post_(\d+)", container.get("id", ""))
            pid = int(post_id_match.group(1)) if post_id_match else 0

            # Extract author
            author_elem = container.find("a", class_="nobname")
            if not author_elem:
                author_elem = container.find("span", class_="b")
            author = author_elem.get_text(strip=True) if author_elem else "匿名"

            # Extract author UID
            uid = ""
            if author_elem and author_elem.get("href"):
                uid_match = re.search(r"uid=(\d+)", author_elem.get("href", ""))
                if uid_match:
                    uid = uid_match.group(1)

            # Extract post time
            post_time = ""
            time_elem = container.find("em", class_="lastpost")
            if time_elem:
                post_time = time_elem.get_text(strip=True)
            else:
                # Try to find in span or div
                time_elem = container.find(["span", "div"], class_=re.compile(r"time|dateline"))
                if time_elem:
                    post_time = time_elem.get_text(strip=True)

            # Extract post content
            content_elem = container.find("div", class_="tpc_content")
            if not content_elem:
                content_elem = container.find("div", class_="pcbs")

            content = ""
            if content_elem:
                # Get text content, preserving structure
                content = self._clean_post_content(content_elem)

            # Extract floor number
            floor = 0
            floor_elem = container.find("span", class_="floors")
            if floor_elem:
                floor_match = re.search(r"#(\d+)", floor_elem.get_text())
                if floor_match:
                    floor = int(floor_match.group(1))

            return {
                "pid": pid,
                "author": author,
                "uid": uid,
                "content": content,
                "post_time": post_time,
                "floor": floor,
            }
        except Exception as e:
            return None

    def _clean_post_content(self, elem):
        """
        Clean post content for terminal display.
        Removes images, preserves text and links.

        Args:
            elem: BeautifulSoup element with post content

        Returns:
            Cleaned text content
        """
        # Clone element to avoid modifying original
        elem = elem.__copy__()

        # Remove images but keep alt text or link
        for img in elem.find_all("img"):
            alt = img.get("alt", "")
            if alt:
                alt = f"[{alt}]"
            img.replace_with(BeautifulSoup(alt or "", "html.parser"))

        # Remove video/audio embeds
        for embed in elem.find_all(["video", "audio", "flash"]):
            embed.decompose()

        # Get text, preserving newlines for paragraphs
        texts = []
        for child in elem.children:
            if hasattr(child, 'name'):
                if child.name in ['br']:
                    texts.append("\n")
                elif child.name in ['p', 'div']:
                    texts.append(child.get_text(strip=True))
                    texts.append("\n")
                else:
                    texts.append(child.get_text(strip=True))
            else:
                texts.append(str(child).strip())

        result = "".join(texts)

        # Clean up extra whitespace
        result = re.sub(r"\n{3,}", "\n\n", result)
        result = result.strip()

        return result

    def reply_thread(self, tid, content, replypid=None):
        """
        Post a reply to a thread.

        Args:
            tid: Thread ID
            content: Reply content
            replypid: Optional PID to quote

        Returns:
            True if successful

        Raises:
            ApiError: If reply fails
        """
        if not self.is_logged_in():
            raise ApiError("请先登录")

        # Get fresh formhash
        formhash = self.get_formhash()

        # Build reply URL
        reply_url = urljoin(self.config.BASE_URL, f"post.php?action=reply&tid={tid}&replysubmit=yes")

        post_data = {
            "m_formhash": formhash,
            "referer": urljoin(self.config.BASE_URL, f"viewthread.php?tid={tid}"),
            "posttime": int(time.time()),
            "subject": "Re: " + str(tid),
            "message": content,
        }

        if replypid:
            post_data["reppost"] = replypid

        response = self.post(reply_url, data=post_data)

        if "succeedhandle" in response or "发帖成功" in response:
            return True
        elif "错误" in response or "失败" in response:
            # Try to extract error message
            error_match = re.search(r"提示:([^\n]+)", response)
            if error_match:
                raise ApiError(f"回复失败: {error_match.group(1)}")
            raise ApiError("回复失败：未知错误")
        else:
            # Check if actually succeeded
            if self._check_post_succeeded(tid):
                return True
            raise ApiError("回复失败：未知错误")

    def _check_post_succeeded(self, tid):
        """Check if a post was successfully created."""
        try:
            html = self.get(self.config.BASE_URL + f"viewthread.php?tid={tid}")
            return True
        except:
            return False

    def get_forum_name(self, fid):
        """
        Get forum name by ID.

        Args:
            fid: Forum ID

        Returns:
            Forum name or "未知板块"
        """
        return self.config.FORUMS.get(fid, "未知板块")
