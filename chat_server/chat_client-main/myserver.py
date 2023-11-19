import socket
import threading
import queue
import select
import json



# num_workers를 통해 thread 수 변경 가능
class ChatServer:
    def __init__(self, port, address, num_workers=2):
        self.port = port
        self.num_workers = num_workers
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((address, port))
        self.server_socket.listen(65535)
        self.clients = {}
        self.rooms = {}
        self.message_queue = queue.Queue()
        self.lock = threading.Lock()
        self.num_workers = num_workers
        self.client_info = {}  # 클라이언트 정보 저장
        self.room_of_client = {}  # 클라이언트의 현재 대화방 저장

        self.message_handlers ={
            'CSName': self.handle_cs_name,
            'CSRooms': self.handle_cs_rooms,
            'CSCreateRoom': self.handle_cs_create_room,
            'CSJoinRoom': self.handle_cs_join_room,
            'CSLeaveRoom': self.handle_cs_leave_room,
            'CSChat': self.handle_cs_chat,            
            'CSShutdown': self.handle_cs_shutdown
        }

        self.host = address        


    def start(self):
        try:
            while True:
                client_socket, address = self.server_socket.accept()
                print(f"Accepted connection from {address}")
                client_thread = threading.Thread(target=self.client_handler, args=(client_socket,))
                client_thread.start()
        except KeyboardInterrupt:
            print("Server shutting down.")
            self.server_socket.close()
        
    def client_handler(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break

                message = data.decode('utf-8')
                json_message = self.parse_json_message(message)

                if json_message:
                    self.process_client_message(client_socket, json_message, self.rooms, self.client_info, self.room_of_client)
                else:
                    print("Received invalid JSON:", message)

            except Exception as e:
                print(f"클라이언트 처리 오류: {e}")
                break

        # 클라이언트가 연결을 끊으면 여기에 추가 정리 로직을 추가할 수 있습니다.
        client_socket.close()
        with self.lock:
            del self.clients[client_socket]
        print(f"클라이언트 연결 종료")
        
    def process_client_message(self, client_socket, message, rooms, client_info, room_of_client):
        try:
            message_type = message.get('type', '')
            handler = self.message_handlers.get(message_type)
            if handler:
                handler(self.clients[client_socket], message)
            else:
                print(f"Unsupported message type: {message_type}")
        except Exception as e:
            print(f"Error processing client message: {e}")

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

    def  broadcast(self, message):
        # 수정: self.members() → self.clients.values()
        for member in self.clients.values():
            try:
                member.sendall(message)
            except socket.error:
                # Handle socket errors if any
                pass

    def handle_cs_name(self, client, message):
        # 클라이언트의 이름 변경 처리
        new_name = message.get('name', '')  # JSON에서 새로운 이름을 가져옵니다.
        
        with self.lock:
            old_name = client.name
            client.name = new_name

            if client.room:
                room_members = [m for m in client.room.members if m != client]
                system_message = f"[시스템 메시지] 이름이 {old_name}에서 {new_name}으로 변경되었습니다."
                self.broadcast(create_chat_json_response('SCSystemMessage', {'content': system_message}), room_members)

                # 클라이언트가 대화방에 있을 때 대화방 멤버들에게 알림

    def handle_cs_rooms(self, client, message):
        # 현재 대화방 목록 전송
        rooms_list = [{'id': room.id, 'title': room.title, 'members': [m.name for m in room.members]} for room in self.rooms.values()]
        response_message = create_rooms_json_response('SCRooms', rooms_list)
        client.send_message(response_message)

    def handle_cs_create_room(self, client, message):
        # 대화방 생성 처리
        if client.room:
            error_message = "[시스템 메시지] 대화 방에 있을 때는 방을 개설할 수 없습니다."
            client.send_message(create_json_response('SCSystemMessage', error_message))
            return

        room_title = message.get('title', '')
        if not room_title:
            error_message = "[시스템 메시지] 방 제목을 입력해주세요."
            client.send_message(create_json_response('SCSystemMessage', error_message))
            return

        with self.lock:
            room_id = len(self.rooms) + 1
            new_room = Room(room_id, room_title)
            new_room.add_member(client)
            self.rooms[room_id] = new_room

            client.room = new_room
            join_message = f"[시스템 메시지] 방제[{room_title}] 방에 입장했습니다."
            self.broadcast(create_chat_json_response('SCSystemMessage', {'content': join_message}), new_room.members)

    def handle_cs_join_room(self, client, message):
        # 대화방 참여 처리
        if client.room:
            error_message = "[시스템 메시지] 대화 방에 있을 때는 다른 방에 들어갈 수 없습니다."
            client.send_message(create_json_response('SCSystemMessage', error_message))
            return

        room_id = message.get('room_id', 0)
        target_room = self.rooms.get(room_id)

        if not target_room:
            error_message = "[시스템 메시지] 대화방이 존재하지 않습니다."
            client.send_message(create_json_response('SCSystemMessage', error_message))
            return

        with self.lock:
            target_room.add_member(client)
            client.room = target_room

            join_message = f"[시스템 메시지] 방제[{target_room.title}] 방에 입장했습니다."
            self.broadcast(create_chat_json_response('SCSystemMessage', {'content': join_message}), target_room.members)

    def handle_cs_leave_room(self, client, message):
        # 대화방 나가기 처리
        if not client.room:
            error_message = "[시스템 메시지] 현재 대화방에 들어가 있지 않습니다."
            client.send_message(create_json_response('SCSystemMessage', error_message))
            return

        with self.lock:
            room_title = client.room.title
            room_members = [m for m in client.room.members if m != client]

            leave_message = f"[시스템 메시지] 방제[{room_title}] 대화 방에서 퇴장했습니다."
            self.broadcast(create_chat_json_response('SCSystemMessage', {'content': leave_message}), room_members)

            client.room.remove_member(client)
            client.room = None

    def handle_cs_shutdown(self, client, message):
        print("Shutting down the server.")
        
        # 예시: 서버 종료 시에는 모든 클라이언트에게 종료 메시지 전송
        shutdown_message = create_json_response('SCSystemMessage', '서버가 종료되었습니다.')
        for member in self.clients.values():
            try:
                member.sendall(shutdown_message.encode('utf-8'))
            except socket.error:
                # Handle socket errors if any
                pass

        self.server_socket.close()
        sys.exit()



class Room:
    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.members = []

    def add_member(self, member):
        self.members.append(member)

    def remove_member(self, member):
        self.members.remove(member)


class Client:
    def __init__(self, socket, address, port):
        self.port = port
        self.socket = socket
        self.address = address
        self.name = f"Guest{port[1]}"  # Guest 이름을 포트 번호로 설정
        self.room = None

    def send_message(self, message):
        try:
            # 메시지의 길이를 2바이트로 변환하여 전송
            message_length = len(message)
            length_bytes = message_length.to_bytes(2, byteorder='big')
            self.socket.sendall(length_bytes)

            # 실제 메시지 전송
            self.socket.sendall(message.encode())
        except Exception as e:
            print("메시지 전송 중 오류 발생:", e)

def handle_client(client_sock, client_info):
    while True:
        try:
            data = client_sock.recv(1024)
            if not data:
                break

            message = data.decode('utf-8')

            try:
                json_message = json.loads(message)
                process_client_message(client_sock, json_message, rooms, client_info, room_of_client)
            except json.JSONDecodeError:
                print("Received invalid JSON:", message)

        except Exception as e:
            print(f"클라이언트 처리 오류: {e}")
            break

    # 클라이언트가 연결을 끊으면 여기에 추가 정리 로직을 추가할 수 있습니다.
    client_sock.close()
    with self.lock:
        del self.clients[client_sock]
    print(f"클라이언트 연결 종료")



def parse_json_message(message):
    try:
        json_message = json.loads(message)
        return json_message
    except json.JSONDecodeError:
        print("jsonDecode 예외 발생")
        return None


def create_rooms_json_response(action, text):
    
    #대화방 목록과 관련된 JSON 응답 메시지를 생성하는 함수.

    #Parameters:
    #- action (str): 메시지의 타입을 나타내는 문자열.
    #- text (list): 대화방 목록을 나타내는 리스트.

    #Returns:
    #- str: 생성된 JSON 형식의 응답 메시지 문자열.
    #"""
    return json.dumps({"type": action, "rooms": text})

def create_json_response(action, text):
    #"""
    #JSON 응답 메시지를 생성하는 함수.

    #Parameters:
    #- action (str): 메시지의 타입을 나타내는 문자열.
    #- text (str): 메시지의 텍스트 내용을 나타내는 문자열.

    #Returns:
    #- str: 생성된 JSON 형식의 응답 메시지 문자열.
    #"""
    return json.dumps({"type": action, "text": text})

def create_chat_json_response(action, content):
    #"""
    #채팅 메시지와 관련된 JSON 응답 메시지를 생성하는 함수.

    #Parameters:
    #- action (str): 메시지의 타입을 나타내는 문자열.
    #- content (dict): 채팅 내용을 나타내는 딕셔너리.

    #Returns:
    #- str: 생성된 JSON 형식의 응답 메시지 문자열.
#"""
    return json.dumps({"type": action, **content})

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

        # 수정: 각 클라이언트의 핸들러에 클라이언트 정보를 추가하여 전달
        clients[client_sock] = threading.Thread(target=handle_client, args=(client_sock, client_info[client_sock]))
        clients[client_sock].start()