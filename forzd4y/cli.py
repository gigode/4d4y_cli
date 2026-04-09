#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4d4y Forum CLI - Main entry point.
A BBS-style terminal client for browsing 4d4y forum.
"""

import sys
import getpass
import tty
import termios
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
        'up', 'down', 'enter', 'quit', or single character
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
        except Exception as e:
            print(f"DEBUG get_key tty exception: {e}", file=sys.stderr)
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

    def __init__(self):
        """Initialize the BBS client."""
        self.config = Config()
        self.api = ForumApi(self.config)
        self.ui = TerminalUI()
        self.current_fid = None
        self.current_tid = None
        self.current_page = 1
        self.logged_in = False

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
                if action is None:
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
            self._browse_forums()
        elif key == '2':
            self._enter_forum(2)  # Discovery fid
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
                self.api.login(username, password)
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
            self.ui.print_forum_list(forums)

            fid_input = get_input("  输入板块编号进入, 或按 Q 返回: ").strip()

            if fid_input.lower() == "q":
                return

            try:
                fid = int(fid_input)
                self._enter_forum(fid)
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
        """
        self.current_fid = fid
        self.current_page = 1
        selected_idx = 0  # Currently selected thread index (0-based)

        while True:
            try:
                threads, total_pages, _ = self.api.get_thread_list(fid, self.current_page)

                if not threads:
                    self.ui.print_message("该板块暂无帖子")
                    break

                # Ensure selected_idx is valid
                if selected_idx >= len(threads):
                    selected_idx = len(threads) - 1
                if selected_idx < 0:
                    selected_idx = 0

                # Display thread list with cursor
                self.ui.print_thread_list(threads, self.current_page, total_pages, fid, selected_idx)

                # Get key input
                key = get_key()

                # DEBUG: print key to stderr
                import sys
                print(f"DEBUG: key={repr(key)}", file=sys.stderr)

                if key == 'quit':
                    break
                elif key == 'b':
                    break
                elif key == 'up':
                    # Move cursor up
                    if selected_idx > 0:
                        selected_idx -= 1
                elif key == 'down':
                    # Move cursor down
                    if selected_idx < len(threads) - 1:
                        selected_idx += 1
                elif key == 'enter':
                    # Open selected thread
                    if threads:
                        self._view_thread(threads[selected_idx])
                elif key == 'r' or key == 'R':
                    if self.logged_in:
                        self.ui.print_message("正在回复帖子...")
                    else:
                        self.ui.print_message("请先登录再回复")
                elif key.isdigit():
                    # Jump to specific thread number
                    idx = int(key) - 1
                    if 0 <= idx < len(threads):
                        selected_idx = idx
                        self._view_thread(threads[idx])

            except ApiError as e:
                self.ui.print_message(f"获取帖子列表失败: {e}", is_error=True)
                break
            except KeyboardInterrupt:
                break

    def _view_thread(self, thread):
        """
        View a thread's posts.

        Args:
            thread: Thread dictionary
        """
        self.current_tid = thread.get("tid")
        self.current_page = 1
        thread_title = thread.get("title", "无标题")

        while True:
            try:
                posts, total_pages, _, title = self.api.get_thread_detail(
                    self.current_tid, self.current_page
                )

                # Use server-provided title if available
                if title:
                    thread_title = title

                self.ui.print_thread_posts(posts, thread_title, self.current_page, total_pages)

                cmd = get_input("  命令 [J/K翻页 R回复 Q返回]: ").strip().lower()

                if cmd == "q":
                    break
                elif cmd == "j":
                    if self.current_page < total_pages:
                        self.current_page += 1
                elif cmd == "k":
                    if self.current_page > 1:
                        self.current_page -= 1
                elif cmd == "r":
                    self._reply_to_thread()
                elif cmd == "h":
                    self.current_page = 1
                elif cmd == "l":
                    self.current_page = total_pages
                elif cmd.isdigit():
                    # Jump to page
                    page = int(cmd)
                    if 1 <= page <= total_pages:
                        self.current_page = page

            except ApiError as e:
                self.ui.print_message(f"获取帖子内容失败: {e}", is_error=True)
                break
            except KeyboardInterrupt:
                break

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
