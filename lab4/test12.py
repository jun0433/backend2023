import json
import sys

def sendto10001(s):
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  server_address = ('127.0.0.1', 10001)
  close(s)

def main(argv):
  obj1 = {
    'name': 'DK Moon',
    'id': 12345678,
    'work': {
      'name': 'Myongji Unviversity',
      'address': '116 Myongji-ro'
      }
    }


  s = json.dumps(obj1)

  data = sendto10001(s)

  obj2 = json.loads(data)
  print(obj2['name'], obj2['id'], obj2['work']['address'])
  print(obj1 == obj2)


if __name__ == '__main__':
  main(sys.argv)