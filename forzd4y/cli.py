#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4d4y Forum CLI - Main entry point.
A BBS-style terminal client for browsing 4d4y forum.
"""

import sys
import getpass
from pathlib import Path

# Add package to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from forzd4y.config import Config
from forzd4y.api import ForumApi, ApiError
from forzd4y.ui import TerminalUI, get_input


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

        choice = get_input("  请选择: ").strip().lower()

        if choice == "q":
            return False
        elif choice == "l":
            self._handle_login()
        elif choice == "1":
            self._browse_forums()
        elif choice == "2":
            self._enter_forum(2)  # Discovery fid
        elif choice == "3":
            self._search_posts()
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
        Enter a specific forum and browse threads.

        Args:
            fid: Forum ID
        """
        self.current_fid = fid
        self.current_page = 1
        forum_name = self.api.get_forum_name(fid)

        while True:
            try:
                threads, total_pages, _ = self.api.get_thread_list(fid, self.current_page)
                self.ui.print_thread_list(threads, self.current_page, total_pages, fid)

                cmd = get_input("  命令 [J/K翻页 Enter查看 R回复 B返回]: ").strip().lower()

                if cmd == "b":
                    break
                elif cmd == "j" or cmd == "k":
                    if cmd == "j" and self.current_page < total_pages:
                        self.current_page += 1
                    elif cmd == "k" and self.current_page > 1:
                        self.current_page -= 1
                elif cmd == "r":
                    self.ui.print_message("请先选择要回复的帖子 (按 Enter 查看)")
                    get_input()
                elif cmd.isdigit():
                    idx = int(cmd) - 1
                    if 0 <= idx < len(threads):
                        self._view_thread(threads[idx])
                else:
                    # Try Enter = view first thread
                    if threads:
                        self._view_thread(threads[0])

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
