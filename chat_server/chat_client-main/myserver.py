import socket
import threading
import queue
import select

class ChatServer:
    def __init__(self, host, port, num_workers=2):
        self.host = host
        self.port = port
        self.num_workers = num_workers
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # Store connected clients
        self.rooms = {}    # Store chat rooms
        self.message_queue = queue.Queue()

    def start(self):
        # Set up the server socket
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        # Start worker threads
        workers = [threading.Thread(target=self.worker) for _ in range(self.num_workers)]
        for worker in workers:
            worker.start()

        print(f"Server listening on {self.host}:{self.port}")

        try:
            while True:
                client_socket, address = self.server_socket.accept()
                print(f"Accepted connection from {address}")
                client_thread = threading.Thread(target=self.client_handler, args=(client_socket,))
                client_thread.start()
        except KeyboardInterrupt:
            print("Server shutting down.")
            self.server_socket.close()

    def worker(self):
        while True:
            message = self.message_queue.get()
            if message:
                self.broadcast(message)

    def broadcast(self, message):
        for client_socket in self.clients.values():
            try:
                client_socket.sendall(message)
            except socket.error:
                # Handle socket errors if any
                pass

    def client_handler(self, client_socket):
        try:
            # Create a message processing thread for the client
            message_thread = threading.Thread(target=self.message_processor, args=(client_socket,))
            message_thread.start()

            while True:
                readable, _, _ = select.select([client_socket], [], [], 1)
                if readable:
                    data = client_socket.recv(1024)
                    if not data:
                        break

                    # Process received data and enqueue for broadcasting
                    self.process_message(data)

                # Check for messages to send to the client
                try:
                    message = self.message_queue.get_nowait()
                    client_socket.sendall(message)
                except queue.Empty:
                    pass

        except socket.error:
            pass
        finally:
            # Remove client from the list when disconnected
            self.remove_client(client_socket)
            client_socket.close()

    def message_processor(self, client_socket):
        while True:
            try:
                message = self.message_queue.get()
                if message:
                    # Process the message, customize this part according to your message format
                    print(f"Processing message for {client_socket.getpeername()}: {message.decode('utf-8')}")
            except queue.Empty:
                pass

    def process_message(self, data):
        # Process incoming messages and enqueue for broadcasting
        # Customize this part according to your message format
        # For example, extract command from data and take appropriate actions
        self.message_queue.put(data)

    def remove_client(self, client_socket):
        # Remove disconnected client from the list
        for room_id, clients in self.rooms.items():
            if client_socket in clients:
                clients.remove(client_socket)
                break

        for user_id, socket in self.clients.items():
            if socket == client_socket:
                print(f"Client {user_id} disconnected.")
                del self.clients[user_id]
                break

class Room:
    def __init__(self, title):
        self.title = title
        self.members = []

    def add_member(self, member):
        self.members.append(member)

    def remove_member(self, member):
        self.members.remove(member)



def process_client_message(client_sock, message, rooms, client_info, room_of_client):
    # ...

    if msg_type == '/name':
        handle_name_command(client_sock, message, client_info, rooms, room_of_client)
    elif msg_type == '/rooms':
        handle_rooms_command(client_sock, rooms)
    elif msg_type == '/create':
        handle_create_command(client_sock, message, rooms, client_info, room_of_client)
    elif msg_type == '/join':
        handle_join_command(client_sock, message, rooms, client_info, room_of_client)
    elif msg_type == '/leave':
        handle_leave_command(client_sock, rooms, client_info, room_of_client)
    elif msg_type == '/shutdown':
        handle_shutdown_command(client_sock, server_sock, client_info, rooms, room_of_client)
    else:
        # Assume it's a chat message
        handle_chat_message(client_sock, message, client_info, room_of_client)



def handle_name_command(client_sock, message, client_info, rooms, room_of_client):
    new_name = message['data']
    old_name = client_info[client_sock]['name']
    client_info[client_sock]['name'] = new_name

    if room_of_client[client_sock]:
        room = rooms[room_of_client[client_sock]]
        sys_msg = f"[시스템 메시지] 이름이 {old_name}에서 {new_name}으로 변경되었습니다."

        for member_sock in room.members:
            send_system_message(member_sock, sys_msg)

    else:
        send_system_message(client_sock, f"[시스템 메시지] 이름이 {old_name}에서 {new_name}으로 변경되었습니다.")

def handle_client(client_sock):
    while True:
        try:
            data = client_sock.recv(1024)
            if not data:
                break

            message = json.loads(data.decode('utf-8'))
            process_client_message(client_sock, message, rooms, client_info, room_of_client)

        except Exception as e:
            print(f"클라이언트 처리 오류: {e}")
            break

    # 클라이언트가 연결을 끊으면 여기에 추가 정리 로직을 추가할 수 있습니다.
    client_sock.close()
    del clients[client_sock]
    print(f"클라이언트 연결 종료: {addr}")


if __name__ == "__main__":
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    host = '127.0.0.1'
    port = 9112

    server_sock.bind((host, port))
    server_sock.listen(5)

    print(f"채팅 서버가 {host}:{port}에서 실행 중입니다.")

    clients = {}
    client_info = {}
    rooms = {}
    room_of_client = {}

    while True:
        client_sock, addr = server_sock.accept()
        print(f"새로운 연결: {addr}")
        client_info[client_sock] = {'name': f'Guest{len(clients) + 1}'}
        clients[client_sock] = threading.Thread(target=handle_client, args=(client_sock,))
        clients[client_sock].start()