import http.server
import socketserver
import os
import sys
import webbrowser
import threading
import base64
import shutil
import tempfile
import _thread  # 新增：用于强制终止线程
from io import BytesIO
from pystray import Icon, Menu, MenuItem
from PIL import Image
from importlib.resources import files, as_file

# 服务器配置
PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler

# 全局变量：新增线程ID用于强制终止
httpd = None
tray_icon = None
temp_web_dir = None
server_thread_id = None  # 存储服务器线程ID，用于强制终止


# 网页资源包配置（目录下需有__init__.py空文件）
WEB_RESOURCES_PACKAGE = "web_resources"

# 托盘图标Base64编码（空占位符，自行填入）
BASE64_ICON = """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"""



def extract_web_resources():
    """提取内置网页资源到临时目录"""
    global temp_web_dir
    try:
        temp_web_dir = tempfile.mkdtemp(prefix="Drawnix_Web_")
        with as_file(files(WEB_RESOURCES_PACKAGE)) as src_dir:
            shutil.copytree(src_dir, temp_web_dir, dirs_exist_ok=True)
        return temp_web_dir
    except Exception as e:
        print(f"提取网页资源失败: {e}")
        cleanup_resources()
        sys.exit(1)


def cleanup_resources():
    """异步清理临时目录，避免文件占用阻塞"""
    global temp_web_dir
    if temp_web_dir and os.path.exists(temp_web_dir):
        # 用线程异步清理，避免阻塞主线程退出
        threading.Timer(0.5, lambda: shutil.rmtree(temp_web_dir, ignore_errors=True)).start()


class StoppableTCPServer(socketserver.TCPServer):
    """自定义服务器：支持立即关闭，不等待请求"""
    allow_reuse_address = True  # 解决端口占用问题
    daemon_threads = True       # 服务器子线程设为守护线程，随主线程退出

    def shutdown(self):
        # 立即关闭服务器监听socket，强制终止serve_forever()
        self.socket.close()
        super().shutdown()


def start_server():
    """启动服务器（记录线程ID，便于强制终止）"""
    global httpd, server_thread_id
    server_thread_id = _thread.get_ident()  # 获取当前线程ID
    try:
        web_dir = extract_web_resources()
        os.chdir(web_dir)
        httpd = StoppableTCPServer(("", PORT), Handler)
        print(f"服务器已启动: http://localhost:{PORT}")
        httpd.serve_forever()  # 若被强制终止，会直接抛出异常
    except Exception as e:
        # 忽略"socket已关闭"的正常退出异常
        if "closed" not in str(e).lower() and "terminated" not in str(e).lower():
            print(f"服务器异常: {e}")
    finally:
        cleanup_resources()


def open_browser(_=None, __=None):
    """打开浏览器访问应用"""
    webbrowser.open_new_tab(f"http://localhost:{PORT}")


def stop_app(icon, _):
    """强制终止所有阻塞项，确保立即退出"""
    global httpd, server_thread_id
    # 1. 立即停止托盘图标（终止托盘阻塞线程）
    if icon:
        icon.stop()

    # 2. 强制关闭服务器（优先关闭socket）
    if httpd:
        httpd.shutdown()
        httpd = None

    # 3. 强制终止服务器线程（关键：解决serve_forever()阻塞）
    if server_thread_id:
        try:
            _thread.exit_thread(server_thread_id)  # 强制终止服务器线程
        except Exception:
            pass  # 忽略线程已终止的异常

    # 4. 清理资源并强制退出程序（不等待任何操作）
    cleanup_resources()
    sys.exit(0)  # 强制终止主线程


def create_tray():
    """创建系统托盘（使用自定义Base64图标）"""
    global tray_icon
    try:
        # 解码自定义Base64图标（确保填入有效编码，否则会报错）
        icon_bytes = base64.b64decode(BASE64_ICON.strip())
        image = Image.open(BytesIO(icon_bytes))
        # 托盘菜单（简化逻辑，减少阻塞点）
        menu = Menu(
            MenuItem("开始", open_browser),
            MenuItem("退出", stop_app)
        )
        tray_icon = Icon("Drawnix_Server", image, "Drawnix服务器", menu)
        return tray_icon
    except Exception as e:
        print(f"托盘创建失败: {e}")
        sys.exit(1)


def main():
    global server_thread
    # 启动服务器线程（设为守护线程，随主线程退出）
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # 1秒后打开浏览器（等待服务器就绪，不阻塞主线程）
    threading.Timer(1, open_browser).start()

    # 启动托盘（阻塞主线程，直到点击退出）
    tray = create_tray()
    tray.run()


if __name__ == "__main__":
    # 隐藏命令行窗口（打包后生效）
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    # 捕获所有异常，确保异常时也能正常退出
    try:
        main()
    except Exception as e:
        print(f"程序异常: {e}")
        cleanup_resources()
        sys.exit(1)
