# -*- coding: utf-8 -*-
"""
Terminal UI module for 4d4y CLI.
Provides BBS-style interface for navigating and reading forum content.
"""

import os
import sys
from typing import List, Dict, Any, Optional, Callable

# ANSI color codes for terminal
class Colors:
    """ANSI escape codes for terminal colors."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class TerminalUI:
    """BBS-style terminal UI renderer."""

    # Box drawing characters
    HORIZONTAL = "─"
    VERTICAL = "│"
    TOP_LEFT = "┌"
    TOP_RIGHT = "┐"
    BOTTOM_LEFT = "└"
    BOTTOM_RIGHT = "┘"
    CROSS = "┼"
    T_DOWN = "┬"
    T_UP = "┴"
    T_RIGHT = "├"
    T_LEFT = "┤"

    # Screen width
    DEFAULT_WIDTH = 80

    DEFAULT_HEIGHT = 24

    def __init__(self, width=None, height=None):
        """
        Initialize terminal UI.

        Args:
            width: Terminal width (defaults to detected or 80)
            height: Terminal height (defaults to detected or 24)
        """
        try:
            terminal_size = os.get_terminal_size()
            self.width = terminal_size.columns
            self.height = terminal_size.lines
        except OSError:
            self.width = width or self.DEFAULT_WIDTH
            self.height = height or self.DEFAULT_HEIGHT
        self.width = min(self.width, 120)  # Cap max width
        self.height = max(self.height, self.DEFAULT_HEIGHT)

    def clear_screen(self):
        """Clear the terminal screen."""
        print("\033[2J\033[H", end="")

    def clear_line(self):
        """Clear current line."""
        print("\033[2K\r", end="")

    def move_cursor(self, row, col):
        """Move cursor to position."""
        print(f"\033[{row};{col}H", end="")

    def hide_cursor(self):
        """Hide cursor."""
        print("\033[?25l", end="")

    def show_cursor(self):
        """Show cursor."""
        print("\033[?25h", end="")

    def bold(self, text):
        """Return bold text."""
        return f"{Colors.BOLD}{text}{Colors.RESET}"

    def cyan(self, text):
        """Return cyan text."""
        return f"{Colors.CYAN}{text}{Colors.RESET}"

    def yellow(self, text):
        """Return yellow text."""
        return f"{Colors.YELLOW}{text}{Colors.RESET}"

    def green(self, text):
        """Return green text."""
        return f"{Colors.GREEN}{text}{Colors.RESET}"

    def red(self, text):
        """Return red text."""
        return f"{Colors.RED}{text}{Colors.RESET}"

    def dim(self, text):
        """Return dim text."""
        return f"{Colors.DIM}{text}{Colors.RESET}"

    def bright_cyan(self, text):
        """Return bright cyan text."""
        return f"{Colors.BRIGHT_CYAN}{text}{Colors.RESET}"

    def bright_green(self, text):
        """Return bright green text."""
        return f"{Colors.BRIGHT_GREEN}{text}{Colors.RESET}"

    def _center_text(self, text, width=None):
        """Center text within width."""
        width = width or self.width
        text = str(text)
        padding = max(0, (width - len(text)) // 2)
        return " " * padding + text

    def _right_text(self, text, width=None):
        """Right-align text within width."""
        width = width or self.width
        text = str(text)
        padding = max(0, width - len(text))
        return " " * padding + text

    def print_header(self, title, subtitle=None):
        """
        Print BBS-style header.

        Args:
            title: Main title
            subtitle: Optional subtitle
        """
        width = self.width
        inner_width = width - 4

        print()
        print(f"  {Colors.CYAN}{self.TOP_LEFT}{self.HORIZONTAL * inner_width}{self.TOP_RIGHT}{Colors.RESET}")
        print(f"  {Colors.CYAN}{self.VERTICAL}{Colors.RESET}{self.bold(self._center_text(title, inner_width)):^{inner_width}}{Colors.CYAN}{self.VERTICAL}{Colors.RESET}")

        if subtitle:
            print(f"  {Colors.CYAN}{self.VERTICAL}{Colors.RESET}{self.dim(self._center_text(subtitle, inner_width)):^{inner_width}}{Colors.CYAN}{self.VERTICAL}{Colors.RESET}")

        print(f"  {Colors.CYAN}{self.BOTTOM_LEFT}{self.HORIZONTAL * inner_width}{self.BOTTOM_RIGHT}{Colors.RESET}")
        print()

    def print_box(self, lines: List[str], title=None):
        """
        Print text in a box.

        Args:
            lines: List of text lines
            title: Optional box title
        """
        width = self.width - 4
        print(f"  {Colors.CYAN}{self.TOP_LEFT}{self.HORIZONTAL * width}{self.TOP_RIGHT}{Colors.RESET}")

        if title:
            print(f"  {Colors.CYAN}{self.VERTICAL}{Colors.RESET} {self.bold(title)} " + " " * (width - len(title) - 1) + f"{Colors.CYAN}{self.VERTICAL}{Colors.RESET}")
            print(f"  {Colors.CYAN}{self.T_DOWN}{self.HORIZONTAL * width}{self.T_UP}{Colors.RESET}")

        for line in lines:
            line = str(line)
            if len(line) > width:
                line = line[:width - 3] + "..."
            print(f"  {Colors.CYAN}{self.VERTICAL}{Colors.RESET} {line}" + " " * (width - len(line)) + f"  {Colors.CYAN}{self.VERTICAL}{Colors.RESET}")

        print(f"  {Colors.CYAN}{self.BOTTOM_LEFT}{self.HORIZONTAL * width}{self.BOTTOM_RIGHT}{Colors.RESET}")

    def print_divider(self, text=None):
        """
        Print a divider line, optionally with text.

        Args:
            text: Optional text to center in divider
        """
        width = self.width - 4

        if text:
            padding = max(0, (width - len(text) - 2) // 2)
            print(f"  {Colors.DIM}{self.HORIZONTAL * padding} {text} {self.HORIZONTAL * (width - padding - len(text) - 2)}{Colors.RESET}")
        else:
            print(f"  {Colors.DIM}{self.HORIZONTAL * width}{Colors.RESET}")

    def print_thread_list(self, threads: List[Dict], page: int = 1, total_pages: int = 1, fid: int = None, selected_idx: int = 0):
        """
        Print BBS-style thread list with cursor.

        Args:
            threads: List of thread dictionaries
            page: Current page
            total_pages: Total pages
            fid: Forum ID for navigation
            selected_idx: Currently selected thread index (0-based)
        """
        # Header
        print()
        print(self.bold(f"{'─' * self.width}"))
        print(self.bold(f"{' 4D4Y Forum ':=^{self.width}}"))
        print(self.bold(f"{'─' * self.width}"))

        # Column headers
        header = f"  {self.bold(' ')}".ljust(4)
        header += f"{self.bold('序号')}".ljust(5)
        header += f"{self.bold('标题')}".ljust(40)
        header += f"{self.bold('作者')}".ljust(12)
        header += f"{self.bold('回复/查看')}".ljust(14)

        print(self.cyan(header))
        print(self.dim("─" * self.width))

        # Thread list with cursor
        for idx, thread in enumerate(threads):
            title = thread.get("title", "无标题")
            if len(title) > 38:
                title = title[:35] + "..."

            author = thread.get("author", "匿名")
            if len(author) > 10:
                author = author[:8] + ".."

            replies = thread.get("reply_count", 0)
            views = thread.get("view_count", 0)

            # Cursor indicator
            if idx == selected_idx:
                cursor = self.green("▶")
            else:
                cursor = " "

            row = f"  {cursor} {idx+1:>3}.".ljust(10)
            row += self.bright_cyan(title).ljust(40)
            row += self.dim(author).ljust(12)
            row += f"{replies}/{views}".ljust(14)

            print(row)

        # Footer
        print(self.dim("─" * self.width))
        page_info = f"第 {page}/{total_pages} 页, 当前第 {selected_idx + 1} 条"
        nav_hint = "[J/K/↑/↓]选择 [H/L]翻页 [Enter]查看 [数字+Enter]直达 [R]刷新 [B]返回 [Q]退出"
        print(f"  {self.dim(page_info):<30} {self.dim(nav_hint):>{self.width - 34}}")
        print()

    def print_post(self, post: Dict, thread_title: str = None, page: int = 1, total_pages: int = 1):
        """
        Print a single post in BBS style.

        Args:
            post: Post dictionary
            thread_title: Thread title
            page: Current page
            total_pages: Total pages
        """
        print()
        print(self.bold(f"{'─' * self.width}"))

        if thread_title:
            print(self.bold(f"{self._center_text(thread_title[:self.width - 4], self.width - 4)}"))

        print(self.bold(f"{'─' * self.width}"))

        # Post header
        floor = post.get("floor", 0)
        author = post.get("author", "匿名")
        post_time = post.get("post_time", "")
        uid = post.get("uid", "")

        header = f"  {self.bold(f'#{floor}')}" if floor else "  "
        header += f" {self.green(author)}"
        if uid:
            header += f" {self.dim(f'(UID:{uid})')}"
        header += f" {self.dim(post_time)}"

        print(self.cyan(header))
        print(self.dim("─" * self.width))

        # Post content
        content = post.get("content", "")
        if content:
            # Word wrap content
            content_lines = self._word_wrap(content, self.width - 4)
            for line in content_lines:
                print(f"  {line}")
        else:
            print(f"  {self.dim('(无内容)')}")

        print()
        print(self.dim("─" * self.width))

        page_info = f"第 {page}/{total_pages} 页"
        nav_hint = "[J/K]上下 [R]回复 [Q]返回"
        print(f"  {self.dim(page_info):<20} {self.dim(nav_hint):>{self.width - 24}}")
        print()

    def print_thread_posts(self, posts: List[Dict], thread_title: str, page: int = 1, total_pages: int = 1, selected_idx: int = 0):
        """
        Print multiple posts for a thread page.

        Args:
            posts: List of post dictionaries
            thread_title: Thread title
            page: Current page
            total_pages: Total pages
            selected_idx: Currently selected post index on the page
        """
        print()
        print(self.bold(f"{'─' * self.width}"))
        print(self.bold(f"{self._center_text(thread_title[:self.width - 4], self.width - 4)}"))
        print(self.bold(f"{'─' * self.width}"))

        for idx, post in enumerate(posts):
            pointer = self.green("▶ ") if idx == selected_idx else "  "

            if post.get("type") == "image":
                image_url = post.get("image_url", "")
                image_label = post.get("image_label", "图片")
                preview = image_url if len(image_url) <= self.width - 12 else image_url[:self.width - 15] + "..."
                print()
                print(self.yellow(f"{pointer}[图] {image_label}"))
                print(f"  {self.dim('│')} {self.cyan(preview)}")
                continue

            floor = post.get("floor", (page - 1) * 20 + idx + 1)
            author = post.get("author", "匿名")
            post_time = post.get("post_time", "")
            content_lines = post.get("display_lines")
            if content_lines is None:
                content = post.get("content", "")
                content_lines = self._word_wrap(content, self.width - 8) if content else ["(无内容)"]
            continuation = ""
            if post.get("continued_before") or post.get("continued_after"):
                markers = []
                if post.get("continued_before"):
                    markers.append("续上")
                if post.get("continued_after"):
                    markers.append("未完")
                continuation = f" {self.dim('[' + '/'.join(markers) + ']')}"

            # Post header
            print()
            print(self.cyan(f"{pointer}┌─ {self.green(author)} {self.dim(post_time)} #{floor}{continuation}"))

            # Post content with padding
            if content_lines:
                for line in content_lines:
                    print(f"  {self.dim('│')} {line}")
            else:
                print(f"  {self.dim('│')} {self.dim('(无内容)')}")

            print(self.cyan(f"  └{'─' * (self.width - 4)}"))

        print()
        page_info = f"第 {page}/{total_pages} 页"
        nav_hint = "[J/K/↑/↓]选择 [Enter]打开图片 [H/L]翻页 [数字+Enter]跳页 [R]刷新 [B]返回 [Q]退出"
        print(f"  {self.dim(page_info):<20} {self.dim(nav_hint):>{self.width - 24}}")
        print()

    def _word_wrap(self, text: str, width: int) -> List[str]:
        """
        Word wrap text to fit within width.

        Args:
            text: Input text
            width: Maximum line width

        Returns:
            List of wrapped lines
        """
        lines = []
        paragraphs = text.split("\n")

        for para in paragraphs:
            if not para:
                lines.append("")
                continue

            words = para.split()
            current_line = ""
            current_length = 0

            for word in words:
                word_length = len(word)

                if current_length == 0:
                    current_line = word
                    current_length = word_length
                elif current_length + word_length + 1 <= width:
                    current_line += " " + word
                    current_length += word_length + 1
                else:
                    lines.append(current_line)
                    current_line = word
                    current_length = word_length

            if current_line:
                lines.append(current_line)

        return lines

    def print_forum_list(self, forums: List[Dict]):
        """
        Print BBS-style forum list.

        Args:
            forums: List of forum dictionaries
        """
        print()
        print(self.bold(f"{'─' * self.width}"))
        print(self.bold(f"{' 4D4Y Forum - 论坛列表 ':=^{self.width}}"))
        print(self.bold(f"{'─' * self.width}"))

        # Sort forums by fid for consistent display
        sorted_forums = sorted(forums, key=lambda x: x.get("fid", 0))

        current_fid = None
        for forum in sorted_forums:
            fid = forum.get("fid")
            name = forum.get("name", "未知板块")
            url = forum.get("url", "")

            # Group by category (rough grouping by fid ranges)
            if fid != current_fid:
                if current_fid is not None:
                    print()
                current_fid = fid

            # Shorten display if needed
            if len(name) > 30:
                name = name[:27] + "..."

            print(f"  {self.cyan(f'[{fid:>3}]')} {self.green(name)}")

        print()
        print(self.dim("─" * self.width))
        print(f"  {self.dim('[Enter]进入板块 [B]返回 [Q]退出 [L]登录/注销')}")
        print()

    def print_login(self):
        """Print login prompt."""
        print()
        print(self.bold(f"{'─' * self.width}"))
        print(self.bold(f"{' 4D4Y Forum - 登录 ':=^{self.width}}"))
        print(self.bold(f"{'─' * self.width}"))
        print()

    def print_message(self, message: str, is_error: bool = False):
        """
        Print a message to the user.

        Args:
            message: Message text
            is_error: Whether this is an error message
        """
        if is_error:
            print(f"  {self.red('错误:')} {message}")
        else:
            print(f"  {self.green('提示:')} {message}")
        print()

    def print_welcome(self):
        """Print welcome screen."""
        self.clear_screen()
        print()
        print(self.bold(f"{Colors.CYAN}{'#' * self.width}"))
        print()
        print(self.bold(self._center_text("4D4Y Forum CLI 客户端", self.width)))
        print(self.bold(self._center_text("仿 BBS 风格的终端论坛浏览工具", self.width)))
        print()
        print(self.dim(self._center_text(f"版本 1.0.1 | 访问 https://www.4d4y.com/forum/", self.width)))
        print()
        print(self.bold(f"{Colors.CYAN}{'#' * self.width}"))
        print()

    def print_goodbye(self):
        """Print goodbye message."""
        print()
        print(self.bold(f"{Colors.CYAN}{'=' * self.width}"))
        print(self.bold(self._center_text("感谢使用 4D4Y Forum CLI", self.width)))
        print(self.bold(self._center_text("再见!", self.width)))
        print(self.bold(f"{Colors.CYAN}{'=' * self.width}"))
        print()


class InteractiveSelector:
    """Interactive menu/list selector with keyboard navigation."""

    def __init__(self, ui: TerminalUI):
        """
        Initialize selector.

        Args:
            ui: TerminalUI instance
        """
        self.ui = ui
        self.selected_index = 0
        self.scroll_offset = 0
        self.items = []
        self.on_select = None
        self.on_action = {}
        self.page_size = 20

    def run(self, items: List[Any], title: str = None, on_select: Callable = None) -> Optional[Any]:
        """
        Run interactive selector.

        Args:
            items: List of items to select from
            on_select: Callback when item is selected

        Returns:
            Selected item or None
        """
        self.items = items
        self.on_select = on_select
        self.selected_index = 0
        self.scroll_offset = 0

        while True:
            self._display(title)
            key = self._get_key()

            if key == "q":
                return None
            elif key == "j" or key == "down":
                self._move_down()
            elif key == "k" or key == "up":
                self._move_up()
            elif key == "enter":
                if 0 <= self.selected_index < len(self.items):
                    item = self.items[self.selected_index]
                    if self.on_select:
                        result = self.on_select(item)
                        if result is not None:
                            return result
            elif key == "g":
                # Go to top
                self.selected_index = 0
                self.scroll_offset = 0
            elif key == "G":
                # Go to bottom
                self.selected_index = len(self.items) - 1
                self.scroll_offset = max(0, self.selected_index - self.page_size + 1)

    def _display(self, title: str = None):
        """Display current selection list."""
        self.ui.clear_screen()

        if title:
            print(self.ui.bold(f"{title}"))
            print(self.ui.dim("─" * self.ui.width))

        visible_items = self.items[self.scroll_offset:self.scroll_offset + self.page_size]

        for idx, item in enumerate(visible_items):
            actual_idx = self.scroll_offset + idx
            is_selected = actual_idx == self.selected_index

            display = self._format_item(item)
            prefix = f"  {self.ui.green('>')} " if is_selected else "    "
            color = self.ui.bright_green if is_selected else lambda x: x

            print(color(f"{prefix}{display}"))

        # Footer
        print()
        print(self.ui.dim("─" * self.ui.width))
        nav = "[J/K]选择 [Enter]确认 [Q]返回"
        print(f"  {self.ui.dim(nav)}")

    def _format_item(self, item) -> str:
        """Format item for display. Override in subclass."""
        if isinstance(item, dict):
            return item.get("name", str(item))
        return str(item)

    def _move_up(self):
        """Move selection up."""
        if self.selected_index > 0:
            self.selected_index -= 1
            if self.selected_index < self.scroll_offset:
                self.scroll_offset -= 1

    def _move_down(self):
        """Move selection down."""
        if self.selected_index < len(self.items) - 1:
            self.selected_index += 1
            if self.selected_index >= self.scroll_offset + self.page_size:
                self.scroll_offset += 1

    def _get_key(self) -> str:
        """Get a single keypress. Simplified version using input."""
        try:
            return input().strip().lower()
        except EOFError:
            return "q"


class ThreadSelector(InteractiveSelector):
    """Selector specifically for threads."""

    def _format_item(self, item) -> str:
        """Format thread for display."""
        if isinstance(item, dict):
            title = item.get("title", "无标题")
            author = item.get("author", "匿名")
            replies = item.get("reply_count", 0)
            return f"{title[:35]:<35} {item.get('author', '匿名'):<10} [{replies}]"
        return str(item)


def get_input(prompt: str = "", password: bool = False) -> str:
    """
    Get user input from terminal.

    Args:
        prompt: Input prompt
        password: Whether to hide input (for passwords)

    Returns:
        User input string
    """
    if password:
        import getpass
        return getpass.getpass(prompt)
    return input(prompt)
