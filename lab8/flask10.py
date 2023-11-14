#!/usr/bin/python3

from flask import Flask
from flask import request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
  method = request.method
  arg1 = request.args.get('arg1')
  op = request.args.get('op')
  arg2 = request.args.get('arg2')
  client = request.headers['User-Agent']

  if op == '+':
    result = arg1 + arg2
  elif op == '*':
    result = arg1 * arg2
  elif op == '-':
    result = arg1 - arg2

  return f'{result}'

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=19112)