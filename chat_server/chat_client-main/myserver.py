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

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 9112
    server = ChatServer(host, port, num_workers=2)
    server.start()