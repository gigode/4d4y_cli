import os
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from forzd4y.cli import BBSClient
from forzd4y.api import ApiError, ForumApi
from forzd4y.config import Config


class BBSClientNavigationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def make_client(self):
        config = Config(config_dir=self.temp_dir.name)
        return BBSClient(config=config)

    def test_run_exits_when_main_menu_requests_quit(self):
        client = self.make_client()

        with patch.object(client.ui, "print_welcome"), \
             patch.object(client.ui, "print_goodbye"), \
             patch.object(client, "_show_main_menu", side_effect=[False]) as show_main_menu:
            client.run()

        self.assertEqual(show_main_menu.call_count, 1)

    def test_main_menu_quit_key_exits_application(self):
        client = self.make_client()

        with patch("forzd4y.cli.get_key", return_value="quit"), \
             patch.object(client.ui, "clear_screen"), \
             patch("builtins.print"):
            self.assertFalse(client._show_main_menu())

    def test_forum_quit_key_exits_application(self):
        client = self.make_client()

        with patch.object(client.api, "get_thread_list", return_value=([{"tid": 1, "title": "demo"}], 1, 1)), \
             patch.object(client.ui, "print_thread_list"), \
             patch.object(client, "_read_command", return_value="q"):
            self.assertFalse(client._enter_forum(2))

    def test_forum_back_key_returns_to_previous_menu(self):
        client = self.make_client()

        with patch.object(client.api, "get_thread_list", return_value=([{"tid": 1, "title": "demo"}], 1, 1)), \
             patch.object(client.ui, "print_thread_list"), \
             patch.object(client, "_read_command", return_value="b"):
            self.assertTrue(client._enter_forum(2))

    def test_thread_view_quit_key_exits_application(self):
        client = self.make_client()

        with patch.object(client.api, "get_thread_detail", return_value=([{"floor": 1, "content": "demo"}], 1, 1, "topic")), \
             patch.object(client.ui, "print_thread_posts"), \
             patch.object(client, "_read_command", return_value="q"):
            self.assertFalse(client._view_thread({"tid": 1, "title": "topic"}))

    def test_browse_forums_quit_key_exits_application(self):
        client = self.make_client()

        with patch.object(client.api, "get_forum_list", return_value=[]), \
             patch.object(client.ui, "print_forum_list"), \
             patch.object(client, "_read_command", return_value="q"):
            self.assertFalse(client._browse_forums())

    def test_config_init_does_not_create_config_dir(self):
        config_root = f"{self.temp_dir.name}/nested/config"
        Config(config_dir=config_root)
        self.assertFalse(os.path.exists(config_root))

    def test_thread_view_paginates_posts_by_twenty_content_lines(self):
        client = self.make_client()
        page_one_posts = [{"floor": i, "content": "\n".join([f"line-{n}" for n in range(10)])} for i in range(1, 5)]

        with patch.object(client.api, "get_thread_detail", return_value=(page_one_posts, 1, 1, "topic")), \
             patch.object(client.ui, "print_thread_posts") as print_thread_posts, \
             patch.object(client, "_read_command", return_value="q"):
            client._view_thread({"tid": 1, "title": "topic"})

        shown_posts = print_thread_posts.call_args.args[0]
        shown_total_pages = print_thread_posts.call_args.args[3]
        self.assertEqual(len(shown_posts), 1)
        self.assertEqual(shown_posts[0]["floor"], 1)
        self.assertEqual(shown_total_pages, 4)
        self.assertLessEqual(sum(len(post["display_lines"]) for post in shown_posts), 20)

    def test_thread_view_single_long_post_stays_on_one_page(self):
        client = self.make_client()
        long_post = {"floor": 1, "content": "\n".join([f"line-{n}" for n in range(45)])}

        pages = client._paginate_thread_posts([long_post, {"floor": 2, "content": "short"}])

        self.assertEqual(len(pages[0]), 1)
        self.assertEqual(pages[0][0]["floor"], 1)
        self.assertTrue(pages[0][0]["continued_after"])
        self.assertTrue(pages[1][0]["continued_before"])
        self.assertLessEqual(sum(len(post["display_lines"]) for post in pages[0]), 20)

    def test_thread_view_page_never_exceeds_visible_height_budget(self):
        client = self.make_client()
        client.ui.height = 24
        posts = [{"floor": 1, "content": "\n".join([f"line-{n}" for n in range(20)])}]

        pages = client._paginate_thread_posts(posts)
        rendered_lines = 7 + sum(len(post["display_lines"]) + 3 for post in pages[0])

        self.assertLessEqual(rendered_lines, client.ui.height - 1)

    def test_thread_list_numeric_command_opens_matching_thread(self):
        client = self.make_client()
        threads = [{"tid": 1, "title": "one"}, {"tid": 2, "title": "two"}]

        with patch.object(client.api, "get_thread_list", return_value=(threads, 1, 1)), \
             patch.object(client.ui, "print_thread_list"), \
             patch.object(client, "_read_command", side_effect=["2", "b"]), \
             patch.object(client, "_view_thread", return_value=True) as view_thread:
            client._enter_forum(2)

        view_thread.assert_called_once_with(threads[1])

    def test_read_command_executes_letter_without_enter(self):
        client = self.make_client()

        with patch("sys.stdin.isatty", return_value=True), \
             patch("forzd4y.cli.get_key", return_value="b"), \
             patch("builtins.print"):
            self.assertEqual(client._read_command("prompt", direct_keys={"b", "q"}), "b")

    def test_read_command_buffers_digits_until_enter(self):
        client = self.make_client()

        with patch("sys.stdin.isatty", return_value=True), \
             patch("forzd4y.cli.get_key", side_effect=["1", "2", "enter"]), \
             patch("builtins.print"):
            self.assertEqual(
                client._read_command("prompt", direct_keys={"b", "q"}, allow_digits=True),
                "12",
            )

    def test_forum_h_key_goes_to_previous_page(self):
        client = self.make_client()
        page_one_threads = [{"tid": 1, "title": "first"}]
        page_two_threads = [{"tid": 2, "title": "second"}]

        with patch.object(
            client.api,
            "get_thread_list",
            side_effect=[(page_two_threads, 2, 2), (page_one_threads, 2, 1)],
        ), patch.object(client.ui, "print_thread_list"), \
            patch.object(client, "_read_command", side_effect=["h", "b"]):
            client._enter_forum(2)

    def test_forum_l_key_goes_to_next_page_even_if_total_pages_is_one(self):
        client = self.make_client()
        page_one_threads = [{"tid": 1, "title": "first"}]
        page_two_threads = [{"tid": 2, "title": "second"}]

        with patch.object(
            client.api,
            "get_thread_list",
            side_effect=[(page_one_threads, 1, 1), (page_two_threads, 1, 2)],
        ), patch.object(client.ui, "print_thread_list"), \
            patch.object(client, "_read_command", side_effect=["l", "b"]):
            client._enter_forum(2)

    def test_return_from_thread_preserves_forum_page_and_selection(self):
        client = self.make_client()
        page_one_threads = [{"tid": 1, "title": "first"}]
        page_two_threads = [{"tid": 2, "title": "second"}, {"tid": 3, "title": "third"}]

        with patch.object(
            client.api,
            "get_thread_list",
            side_effect=[(page_one_threads, 2, 1), (page_two_threads, 2, 2)],
        ), patch.object(client.ui, "print_thread_list") as print_thread_list, \
            patch.object(client, "_read_command", side_effect=["l", "down", "enter", "b"]), \
            patch.object(client, "_view_thread", return_value=True):
            client._enter_forum(2)

        last_call = print_thread_list.call_args_list[-1]
        self.assertEqual(last_call.args[1], 2)
        self.assertEqual(last_call.args[4], 1)

    def test_forum_navigation_uses_cached_page_data_for_cursor_moves(self):
        client = self.make_client()
        threads = [{"tid": 1, "title": "first"}, {"tid": 2, "title": "second"}]

        with patch.object(client.api, "get_thread_list", return_value=(threads, 1, 1)) as get_thread_list, \
             patch.object(client.ui, "print_thread_list"), \
             patch.object(client, "_read_command", side_effect=["down", "up", "b"]):
            client._enter_forum(2)

        self.assertEqual(get_thread_list.call_count, 1)

    def test_forum_refresh_invalidates_current_page_cache(self):
        client = self.make_client()
        first = ([{"tid": 1, "title": "first"}], 1, 1)
        second = ([{"tid": 1, "title": "updated"}], 1, 1)

        with patch.object(client.api, "get_thread_list", side_effect=[first, second]) as get_thread_list, \
             patch.object(client.ui, "print_thread_list"), \
             patch.object(client, "_read_command", side_effect=["r", "b"]):
            client._enter_forum(2)

        self.assertEqual(get_thread_list.call_count, 2)

    def test_thread_refresh_reloads_thread_pages(self):
        client = self.make_client()

        with patch.object(
            client.api,
            "get_thread_detail",
            side_effect=[
                ([{"floor": 1, "content": "old"}], 1, 1, "topic"),
                ([{"floor": 1, "content": "new"}], 1, 1, "topic"),
            ],
        ) as get_thread_detail, \
            patch.object(client.ui, "print_thread_posts"), \
            patch.object(client, "_read_command", side_effect=["r", "q"]):
            client._view_thread({"tid": 1, "title": "topic"})

        self.assertEqual(get_thread_detail.call_count, 2)

    def test_thread_view_enter_on_image_opens_viewer(self):
        client = self.make_client()
        post_with_image = [{"floor": 1, "content": "hello", "images": [{"url": "https://img.example/test.jpg", "alt": "图"}]}]

        with patch.object(client.api, "get_thread_detail", return_value=(post_with_image, 1, 1, "topic")), \
             patch.object(client.ui, "print_thread_posts"), \
             patch.object(client, "_read_command", side_effect=["k", "enter", "q"]), \
             patch.object(client, "_open_url", return_value=True) as open_browser:
            client._view_thread({"tid": 1, "title": "topic"})

        open_browser.assert_called_once_with("https://img.example/test.jpg")

    def test_thread_view_enter_on_reply_link_opens_browser(self):
        client = self.make_client()
        post_with_link = [{
            "floor": 1,
            "content": "hello",
            "links": [{"url": "https://example.com/post/1", "text": "原帖链接"}],
        }]

        with patch.object(client.api, "get_thread_detail", return_value=(post_with_link, 1, 1, "topic")), \
             patch.object(client.ui, "print_thread_posts"), \
             patch.object(client, "_read_command", side_effect=["k", "enter", "q"]), \
             patch.object(client, "_open_url", return_value=True) as open_browser:
            client._view_thread({"tid": 1, "title": "topic"})

        open_browser.assert_called_once_with("https://example.com/post/1")

    def test_open_url_uses_quiet_xdg_open_when_available(self):
        client = self.make_client()

        with patch("forzd4y.cli.shutil.which", return_value="/usr/bin/xdg-open"), \
             patch("forzd4y.cli.subprocess.Popen") as popen, \
             patch("forzd4y.cli.webbrowser.open") as web_open:
            result = client._open_url("https://img.example/test.jpg")

        self.assertTrue(result)
        popen.assert_called_once()
        web_open.assert_not_called()

    def test_handle_login_shows_error_and_keeps_logged_out_when_api_rejects_credentials(self):
        client = self.make_client()

        with patch.object(client.ui, "print_login"), \
             patch("forzd4y.cli.get_input", side_effect=["tester", ""]), \
             patch("forzd4y.cli.getpass.getpass", return_value="wrong-password"), \
             patch.object(client.api, "login", side_effect=ApiError("登录失败：用户名或密码错误")), \
             patch.object(client.ui, "print_message") as print_message:
            client._handle_login()

        self.assertFalse(client.logged_in)
        print_message.assert_any_call("登录失败：用户名或密码错误", is_error=True)


class ForumApiParsingTests(unittest.TestCase):
    def test_extract_thread_stats_from_single_num_cell(self):
        with TemporaryDirectory() as temp_dir:
            api = ForumApi(config=Config(config_dir=temp_dir))
            html = """
            <tbody id="normalthread_1">
              <tr>
                <td class="icon"></td>
                <th>
                  <a href="viewthread.php?tid=123">测试帖子</a>
                </th>
                <td class="by"><a href="space.php?username=tester">tester</a></td>
                <td class="num">
                  <a href="viewthread.php?tid=123&amp;extra=page%3D1">17</a>
                  <em>245</em>
                </td>
              </tr>
            </tbody>
            """

            threads, _, _ = api._parse_thread_list(html, fid=2, page=1)

        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]["reply_count"], 17)
        self.assertEqual(threads[0]["view_count"], 245)

    def test_extract_post_images(self):
        with TemporaryDirectory() as temp_dir:
            api = ForumApi(config=Config(config_dir=temp_dir))
            html = """
            <td class="t_msgfont">
              <p>text</p>
              <img src="images/icon.gif" alt="gif" />
              <img src="images/demo.jpg" alt="demo" />
              <img src="images/demo.jpeg" alt="demo2" />
              <img file="https://cdn.example/test.png" />
            </td>
            """
            from bs4 import BeautifulSoup
            elem = BeautifulSoup(html, "html.parser").find("td")

            images = api._extract_post_images(elem)

        self.assertEqual(len(images), 2)
        self.assertEqual(images[0]["url"], "https://www.4d4y.com/forum/images/demo.jpg")
        self.assertEqual(images[1]["url"], "https://www.4d4y.com/forum/images/demo.jpeg")

    def test_extract_post_links_skips_image_and_javascript_links(self):
        with TemporaryDirectory() as temp_dir:
            api = ForumApi(config=Config(config_dir=temp_dir))
            html = """
            <td class="t_msgfont">
              <a href="https://example.com/article">外部链接</a>
              <a href="viewthread.php?tid=123">站内帖子</a>
              <a href="images/demo.jpg">图片链接</a>
              <a href="javascript:void(0)">无效</a>
            </td>
            """
            from bs4 import BeautifulSoup
            elem = BeautifulSoup(html, "html.parser").find("td")

            links = api._extract_post_links(elem)

        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["url"], "https://example.com/article")
        self.assertEqual(links[0]["text"], "外部链接")
        self.assertEqual(links[1]["url"], "https://www.4d4y.com/forum/viewthread.php?tid=123")

    def test_check_logged_in_does_not_treat_logged_out_homepage_as_logged_in(self):
        with TemporaryDirectory() as temp_dir:
            api = ForumApi(config=Config(config_dir=temp_dir))
            html = """
            <html>
              <body>
                <a href="space.php?uid=42">someone_else</a>
                <a href="register.php">注册</a>
                <a href="member.php?mod=logging&action=login">登录</a>
              </body>
            </html>
            """

            with patch.object(api, "get", return_value=html):
                self.assertFalse(api._check_logged_in("tester"))

    def test_login_raises_for_wrong_password_and_clears_login_state(self):
        with TemporaryDirectory() as temp_dir:
            config = Config(config_dir=temp_dir)
            config.logged_in = True
            config.uid = "123"
            config.formhash = "deadbeef"
            api = ForumApi(config=config)

            with patch.object(api, "get_formhash", return_value="feedbeef"), \
                 patch.object(api, "post", return_value="密码错误"), \
                 patch.object(api, "_save_cookies"):
                with self.assertRaisesRegex(ApiError, "用户名或密码错误"):
                    api.login("tester", "wrong-password")

            self.assertFalse(config.logged_in)
            self.assertEqual(config.uid, "")
            self.assertEqual(config.formhash, "")


if __name__ == "__main__":
    unittest.main()
