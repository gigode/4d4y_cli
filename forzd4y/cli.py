#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4d4y Forum CLI - Main entry point.
A BBS-style terminal client for browsing 4d4y forum.
"""

import sys
import math
import getpass
import os
import shutil
import subprocess
import tty
import termios
import webbrowser
from pathlib import Path

# Add package to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from forzd4y.config import Config
from forzd4y.api import ForumApi, ApiError
from forzd4y.ui import TerminalUI, get_input


def get_key():
    """
    Get a single keypress including arrow keys.
    Returns:
        'up', 'down', 'enter', 'quit', 'backspace', or single character
    """
    import sys
    # Check if stdin is a tty (interactive terminal)
    if sys.stdin.isatty():
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
            try:
                ch = sys.stdin.read(1)
                if ch == '\x1b':  # Escape sequence
                    seq = sys.stdin.read(2)
                    if seq == '[A':
                        return 'up'
                    elif seq == '[B':
                        return 'down'
                    return 'escape'
                elif ch == '\r':
                    return 'enter'
                elif ch == '\n':
                    return 'enter'
                elif ch in ('\x7f', '\b'):
                    return 'backspace'
                elif ch == 'q' or ch == 'Q':
                    return 'quit'
                elif ch == 'j' or ch == 'J':
                    return 'down'
                elif ch == 'k' or ch == 'K':
                    return 'up'
                elif ch == 'b' or ch == 'B':
                    return 'b'
                else:
                    return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            return 'escape'
    else:
        # Non-interactive (piped input) - use regular input with Enter
        try:
            result = input()
            result = result.strip().lower()
            if result == 'q':
                return 'quit'
            return result
        except EOFError:
            return 'quit'


class BBSClient:
    """Main BBS client application."""
    THREADS_PER_PAGE = 20
    THREAD_VIEW_LINES = 20
    THREAD_VIEW_RESERVED_LINES = 8

    def __init__(self, config=None, api=None, ui=None):
        """Initialize the BBS client."""
        self.config = config or Config()
        self.api = api or ForumApi(self.config)
        self.ui = ui or TerminalUI()
        self.current_fid = None
        self.current_tid = None
        self.current_page = 1
        self.logged_in = False

    def _normalize_key(self, key):
        """Normalize raw key names into command tokens."""
        if key == "quit":
            return "q"
        if isinstance(key, str) and len(key) == 1:
            return key.lower()
        return key

    def _read_command(self, prompt, direct_keys=None, allow_digits=False):
        """
        Read a command from terminal.

        Direct letter commands execute immediately.
        Numeric input is buffered and submitted on Enter.
        """
        direct_keys = set(direct_keys or [])

        if not sys.stdin.isatty():
            command = get_input(prompt).strip().lower()
            return command or "enter"

        buffer = ""
        print(prompt, end="", flush=True)

        while True:
            key = self._normalize_key(get_key())

            if key == "enter":
                print()
                return buffer or "enter"

            if key == "backspace":
                buffer = buffer[:-1]
            elif allow_digits and isinstance(key, str) and key.isdigit():
                buffer += key
            elif key in direct_keys:
                print()
                return key

            self.ui.clear_line()
            print(f"{prompt}{buffer}", end="", flush=True)

    def _open_url(self, url):
        """Open a URL in the system browser without polluting the terminal."""
        opener = shutil.which("xdg-open")
        if opener:
            subprocess.Popen(
                [opener, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
                env={**os.environ, "BROWSER": os.environ.get("BROWSER", "")},
            )
            return True

        return webbrowser.open(url)

    def _get_post_content_lines(self, post):
        """Return wrapped content lines for a post."""
        content = post.get("content", "")
        return self.ui._word_wrap(content, self.ui.width - 8) if content else ["(无内容)"]

    def _paginate_thread_posts(self, posts):
        """Paginate posts by visible screen height and content-line budget."""
        max_content_lines = self.THREAD_VIEW_LINES
        max_rendered_lines = max(1, self.ui.height - self.THREAD_VIEW_RESERVED_LINES)
        pages = []
        current_page = []
        current_content_lines = 0
        current_rendered_lines = 0

        for post in posts:
            wrapped_lines = self._get_post_content_lines(post)
            offset = 0

            while offset < len(wrapped_lines):
                available_content = max_content_lines - current_content_lines
                available_rendered = max_rendered_lines - current_rendered_lines - 3

                if available_content <= 0 or available_rendered <= 0:
                    pages.append(current_page)
                    current_page = []
                    current_content_lines = 0
                    current_rendered_lines = 0
                    continue

                chunk_size = min(len(wrapped_lines) - offset, available_content, available_rendered)
                if chunk_size <= 0:
                    chunk_size = 1

                chunk = dict(post)
                chunk["display_lines"] = wrapped_lines[offset:offset + chunk_size]
                chunk["continued_before"] = offset > 0
                chunk["continued_after"] = offset + chunk_size < len(wrapped_lines)
                current_page.append(chunk)
                current_content_lines += chunk_size
                current_rendered_lines += chunk_size + 3
                offset += chunk_size

                if offset < len(wrapped_lines):
                    pages.append(current_page)
                    current_page = []
                    current_content_lines = 0
                    current_rendered_lines = 0

            for image_index, image in enumerate(post.get("images", []), start=1):
                if current_rendered_lines + 2 > max_rendered_lines:
                    pages.append(current_page)
                    current_page = []
                    current_content_lines = 0
                    current_rendered_lines = 0

                current_page.append({
                    "type": "image",
                    "floor": post.get("floor"),
                    "image_url": image.get("url"),
                    "image_label": image.get("alt") or f"图片 {image_index}",
                })
                current_rendered_lines += 2

        if current_page:
            pages.append(current_page)

        return pages or [[]]

    def _load_thread_pages(self, tid):
        """Load all server pages for a thread and build client-side view pages."""
        all_posts = []
        thread_title = None
        server_page = 1

        while True:
            posts, total_server_pages, _, title = self.api.get_thread_detail(tid, server_page)
            all_posts.extend(posts)
            if title:
                thread_title = title
            if server_page >= total_server_pages:
                break
            server_page += 1

        return self._paginate_thread_posts(all_posts), thread_title or "无标题"

    def _invalidate_thread(self):
        """Clear cached thread view state so the next render reloads data."""
        return None

    def run(self):
        """Main application loop."""
        self.ui.print_welcome()

        # Check if previously logged in
        if self.config.logged_in:
            try:
                if self.api.is_logged_in():
                    self.logged_in = True
                    self.ui.print_message(f"欢迎回来, {self.config.username}!")
                else:
                    self.ui.print_message("会话已过期, 请重新登录")
            except Exception as e:
                self.ui.print_message(f"恢复会话失败: {e}")

        while True:
            try:
                action = self._show_main_menu()
                if action is False:
                    break
            except KeyboardInterrupt:
                self.ui.print_message("按 Q 退出")
                continue
            except Exception as e:
                self.ui.print_message(f"发生错误: {e}", is_error=True)

        self.ui.print_goodbye()

    def _show_main_menu(self):
        """
        Show main menu and handle navigation.

        Returns:
            False to quit, True to continue
        """
        self.ui.clear_screen()

        # Header
        print(self.ui.bold(f"{'─' * self.ui.width}"))
        print(self.ui.bold(f"{' 4D4Y Forum ':=^{self.ui.width}}"))
        print(self.ui.bold(f"{'─' * self.ui.width}"))

        # Status bar
        if self.logged_in:
            status = f"已登录: {self.ui.green(self.config.username)}"
        else:
            status = self.ui.red("未登录")

        print(f"  {status}")
        print(self.ui.dim("─" * self.ui.width))

        # Menu options
        print(self.ui.cyan("  [1] ") + "浏览论坛板块")
        print(self.ui.cyan("  [2] ") + "进入 Discovery 板块")
        print(self.ui.cyan("  [3] ") + "搜索帖子")
        print()
        print(self.ui.cyan("  [L] ") + ("注销" if self.logged_in else "登录"))
        print(self.ui.cyan("  [Q] ") + "退出")
        print()
        print(self.ui.dim("─" * self.ui.width))

        # Show hint based on terminal mode
        if sys.stdin.isatty():
            print(self.ui.dim("  按键选择: "))
        else:
            print(self.ui.dim("  输入选择后按回车: "))

        key = get_key()

        if key in ('quit', 'q', 'Q'):
            return False
        elif key == '1':
            if self._browse_forums() is False:
                return False
        elif key == '2':
            result = self._enter_forum(2)  # Discovery fid
            if result is False:
                return False
        elif key == '3':
            self._search_posts()
        elif key in ('l', 'L'):
            self._handle_login()
        else:
            self.ui.print_message("无效选择")

        return True

    def _handle_login(self):
        """Handle login process."""
        if self.logged_in:
            # Logout
            confirm = get_input("  确定要注销吗? [y/N]: ").strip().lower()
            if confirm == "y":
                self.api.logout()
                self.logged_in = False
                self.ui.print_message("已注销")
        else:
            # Login
            self.ui.print_login()

            username = get_input("  用户名: ").strip()
            if not username:
                self.ui.print_message("用户名不能为空")
                return

            password = getpass.getpass("  密码: ")
            if not password:
                self.ui.print_message("密码不能为空")
                return

            try:
                if self.api.login(username, password):
                    self.logged_in = True
                    self.ui.print_message(f"登录成功! 欢迎, {username}!")
            except ApiError as e:
                self.ui.print_message(str(e), is_error=True)
            except Exception as e:
                self.ui.print_message(f"登录失败: {e}", is_error=True)

        get_input("  按 Enter 继续...")

    def _browse_forums(self):
        """Browse and select a forum."""
        try:
            forums = self.api.get_forum_list()
            while True:
                self.ui.clear_screen()
                self.ui.print_forum_list(forums)
                command = self._read_command(
                    "  输入板块编号后回车, [B]返回, [Q]退出: ",
                    direct_keys={"b", "q"},
                    allow_digits=True,
                )

                if command == "q":
                    return False

                if command == "b":
                    return

                try:
                    return self._enter_forum(int(command))
                except ValueError:
                    self.ui.print_message("请输入有效的板块编号")
                    get_input("  按 Enter 继续...")

        except ApiError as e:
            self.ui.print_message(f"获取板块列表失败: {e}", is_error=True)
            get_input("  按 Enter 继续...")

    def _enter_forum(self, fid):
        """
        Enter a specific forum and browse threads with cursor navigation.

        Args:
            fid: Forum ID

        Returns:
            False to quit the application, True to return to caller
        """
        self.current_fid = fid
        forum_page = 1
        selected_idx = 0  # Currently selected thread index (0-based)
        page_cache = {}

        while True:
            try:
                if forum_page not in page_cache:
                    page_cache[forum_page] = self.api.get_thread_list(fid, forum_page)

                threads, total_pages, _ = page_cache[forum_page]
                threads = threads[:self.THREADS_PER_PAGE]

                if not threads:
                    if forum_page > 1:
                        page_cache.pop(forum_page, None)
                        forum_page -= 1
                        self.ui.print_message("已经是最后一页")
                        get_input("  按 Enter 继续...")
                        continue
                    self.ui.print_message("该板块暂无帖子")
                    break

                # Ensure selected_idx is valid
                if selected_idx >= len(threads):
                    selected_idx = len(threads) - 1
                if selected_idx < 0:
                    selected_idx = 0

                # Display thread list with cursor
                self.ui.clear_screen()
                self.ui.print_thread_list(threads, forum_page, total_pages, fid, selected_idx)

                key = self._read_command(
                    "  命令 [J/K/↑/↓选择 H/L翻页 Enter查看 数字+Enter直达 R刷新 B返回 Q退出]: ",
                    direct_keys={"b", "q", "r", "h", "l", "up", "down"},
                    allow_digits=True,
                )

                if key == 'q':
                    return False
                elif key == 'b':
                    return True
                elif key == 'up':
                    # Move cursor up
                    if selected_idx > 0:
                        selected_idx -= 1
                    elif forum_page > 1:
                        forum_page -= 1
                        selected_idx = self.THREADS_PER_PAGE - 1
                elif key == 'down':
                    # Move cursor down
                    if selected_idx < len(threads) - 1:
                        selected_idx += 1
                    elif forum_page < total_pages:
                        forum_page += 1
                        selected_idx = 0
                elif key == 'h':
                    if forum_page > 1:
                        forum_page -= 1
                        selected_idx = 0
                elif key == 'l':
                    forum_page += 1
                    selected_idx = 0
                elif key == 'enter':
                    # Open selected thread
                    if threads:
                        result = self._view_thread(threads[selected_idx])
                        if result is False:
                            return False
                elif key == "r":
                    page_cache.pop(forum_page, None)
                elif key.isdigit():
                    idx = int(key) - 1
                    if 0 <= idx < len(threads):
                        selected_idx = idx
                        result = self._view_thread(threads[idx])
                        if result is False:
                            return False
                    else:
                        self.ui.print_message("帖子编号超出当前页范围")
                        get_input("  按 Enter 继续...")

            except ApiError as e:
                self.ui.print_message(f"获取帖子列表失败: {e}", is_error=True)
                return True
            except KeyboardInterrupt:
                return True

        return True

    def _view_thread(self, thread):
        """
        View a thread's posts.

        Args:
            thread: Thread dictionary

        Returns:
            False to quit the application, True to return to caller
        """
        self.current_tid = thread.get("tid")
        thread_page = 1
        thread_title = thread.get("title", "无标题")
        selected_idx = 0
        pages = None

        while True:
            try:
                if pages is None:
                    pages, loaded_title = self._load_thread_pages(self.current_tid)
                    if loaded_title:
                        thread_title = loaded_title

                total_pages = len(pages)
                if thread_page > total_pages:
                    thread_page = total_pages
                posts = pages[thread_page - 1]
                if posts:
                    selected_idx = max(0, min(selected_idx, len(posts) - 1))
                else:
                    selected_idx = 0

                self.ui.clear_screen()
                self.ui.print_thread_posts(
                    posts,
                    thread_title,
                    thread_page,
                    total_pages,
                    selected_idx=selected_idx,
                )

                cmd = self._read_command(
                    "  命令 [J/K/↑/↓选择 H/L翻页 R刷新 B返回 Q退出 数字+Enter跳页]: ",
                    direct_keys={"j", "k", "r", "b", "q", "h", "l", "up", "down"},
                    allow_digits=True,
                )

                if cmd == "q":
                    return False
                elif cmd == "b":
                    return True
                elif cmd == "enter":
                    selected_item = posts[selected_idx] if posts else None
                    if selected_item and selected_item.get("type") == "image":
                        try:
                            opened = self._open_url(selected_item.get("image_url"))
                            if not opened:
                                raise RuntimeError("系统未返回可用浏览器")
                        except Exception as exc:
                            self.ui.print_message(f"打开浏览器失败: {exc}", is_error=True)
                            get_input("  按 Enter 继续...")
                elif cmd in {"j", "down"}:
                    if selected_idx < len(posts) - 1:
                        selected_idx += 1
                    elif thread_page < total_pages:
                        thread_page += 1
                        selected_idx = 0
                elif cmd in {"k", "up"}:
                    if selected_idx > 0:
                        selected_idx -= 1
                    elif thread_page > 1:
                        thread_page -= 1
                        previous_posts = pages[thread_page - 1]
                        selected_idx = max(0, len(previous_posts) - 1)
                elif cmd == "r":
                    pages = self._invalidate_thread()
                elif cmd == "h":
                    if thread_page > 1:
                        thread_page -= 1
                        selected_idx = 0
                elif cmd == "l":
                    if thread_page < total_pages:
                        thread_page += 1
                        selected_idx = 0
                elif cmd.isdigit():
                    # Jump to page
                    page = int(cmd)
                    if 1 <= page <= total_pages:
                        thread_page = page
                        selected_idx = 0

            except ApiError as e:
                self.ui.print_message(f"获取帖子内容失败: {e}", is_error=True)
                return True
            except KeyboardInterrupt:
                return True

        return True

    def _reply_to_thread(self):
        """Reply to the current thread."""
        if not self.logged_in:
            self.ui.print_message("请先登录再回复")
            return

        if not self.current_tid:
            self.ui.print_message("未选择帖子")
            return

        print()
        print(self.ui.bold("  ── 回复帖子 ──"))
        print(self.ui.dim("  (输入空行取消)"))
        print()

        lines = []
        print("  ", end="")
        while True:
            try:
                line = input()
                if line == "":
                    # Check if we should cancel
                    if not lines:
                        self.ui.print_message("已取消回复")
                        return
                    break
                lines.append(line)
                print("  ", end="")
            except EOFError:
                break
            except KeyboardInterrupt:
                self.ui.print_message("已取消回复")
                return

        if lines:
            content = "\n".join(lines)
            try:
                self.api.reply_thread(self.current_tid, content)
                self.ui.print_message("回复成功!")
            except ApiError as e:
                self.ui.print_message(f"回复失败: {e}", is_error=True)

        get_input("  按 Enter 继续...")

    def _search_posts(self):
        """Search for posts."""
        self.ui.clear_screen()
        print(self.ui.bold(f"{'─' * self.ui.width}"))
        print(self.ui.bold(f"{' 搜索帖子 ':=^{self.ui.width}}"))
        print(self.ui.bold(f"{'─' * self.ui.width}"))
        print()

        keyword = get_input("  输入搜索关键词: ").strip()

        if not keyword:
            self.ui.print_message("关键词不能为空")
            return

        self.ui.print_message("搜索功能开发中...")
        get_input("  按 Enter 继续...")


def main():
    """Main entry point."""
    try:
        client = BBSClient()
        client.run()
    except KeyboardInterrupt:
        print("\n\n再见!")
        sys.exit(0)
    except Exception as e:
        print(f"严重错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
