from http import HTTPStatus
import random
import requests
import json
import urllib
import mysql.connector

from flask import abort, Flask, make_response, render_template, Response, redirect, request, jsonify

app = Flask(__name__)

# MySQL 연결 정보
db_config = {
    'host': '127.0.0.1',
    'user': '1111',
    'password': '1111',
    'database': '1111',
}

# MySQL 연결
db_connection = mysql.connector.connect(**db_config)
cursor = db_connection.cursor()

naver_client_id = 'kJUs5y8A5tPUZETNrEgO'
naver_client_secret = 'uYW8foMK4L'
naver_redirect_uri = 'http://localhost:8000/auth'
'''
  본인 app 의 것으로 교체할 것.
  여기 지정된 url 이 http://localhost:8000/auth 처럼 /auth 인 경우
  아래 onOAuthAuthorizationCodeRedirected() 에 @app.route('/auth') 태깅한 것처럼 해야 함
'''


@app.route('/')
def home():
    # 쿠기를 통해 이전에 로그인 한 적이 있는지를 확인한다.
    # 이 부분이 동작하기 위해서는 OAuth 에서 access token 을 얻어낸 뒤
    # user profile REST api 를 통해 유저 정보를 얻어낸 뒤 'userId' 라는 cookie 를 지정해야 된다.
    # (참고: 아래 onOAuthAuthorizationCodeRedirected() 마지막 부분 response.set_cookie('userId', user_id) 참고)
    userId = request.cookies.get('userId', default=None)
    name = None
    ####################################################
    # TODO: 아래 부분을 채워 넣으시오.
    #       userId 로부터 DB 에서 사용자 이름을 얻어오는 코드를 여기에 작성해야 함
    if userId:
        # userId로부터 DB에서 사용자 이름을 얻어오는 쿼리 실행
        query = "SELECT user_name FROM user_table WHERE user_id = %s"
        cursor.execute(query, (userId,))
        result = cursor.fetchone()

        if result:
            name = result[0]
    ####################################################


    # 이제 클라에게 전송해 줄 index.html 을 생성한다.
    # template 로부터 받아와서 name 변수 값만 교체해준다.
    return render_template('index.html', name=name)


# 로그인 버튼을 누른 경우 이 API 를 호출한다.
# OAuth flow 상 브라우저에서 해당 URL 을 바로 호출할 수도 있으나,
# 브라우저가 CORS (Cross-origin Resource Sharing) 제약 때문에 HTML 을 받아온 서버가 아닌 곳에
# HTTP request 를 보낼 수 없는 경우가 있다. (예: 크롬 브라우저)
# 이를 우회하기 위해서 브라우저가 호출할 URL 을 HTML 에 하드코딩하지 않고,
# 아래처럼 서버가 주는 URL 로 redirect 하는 것으로 처리한다.
#
# 주의! 아래 API 는 잘 동작하기 때문에 손대지 말 것
@app.route('/login')
def onLogin():
    params={
            'response_type': 'code',
            'client_id': naver_client_id,
            'redirect_uri': naver_redirect_uri,
            'state': random.randint(0, 10000)
        }
    urlencoded = urllib.parse.urlencode(params)
    url = f'https://nid.naver.com/oauth2.0/authorize?{urlencoded}'
    return redirect(url)


# 아래는 Redirect URI 로 등록된 경우 호출된다.
# 만일 본인의 Redirect URI 가 http://localhost:8000/auth 의 경우처럼 /auth 대신 다른 것을
# 사용한다면 아래 @app.route('/auth') 의 내용을 그 URL 로 바꿀 것
@app.route('/auth')
def onOAuthAuthorizationCodeRedirected():
    # TODO: 아래 1 ~ 4 를 채워 넣으시오.

    # 1. redirect uri 를 호출한 request 로부터 authorization code 와 state 정보를 얻어낸다.
    authorization_code = request.args.get('code')
    state = request.args.get('state')



    # 2. authorization code 로부터 access token 을 얻어내는 네이버 API 를 호출한다.
    token_url = 'https://nid.naver.com/oauth2.0/token'
    token_params = {
        'client_id': naver_client_id,
        'client_secret': naver_client_secret,
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'state': state,
        'redirectURI': naver_redirect_uri,
    }
    response = requests.post(token_url, params=token_params)
    token_json = response.json()
    access_token = token_json['access_token']


    # 3. 얻어낸 access token 을 이용해서 프로필 정보를 반환하는 API 를 호출하고,
    #    유저의 고유 식별 번호를 얻어낸다.
    user_info_url = 'https://openapi.naver.com/v1/nid/me'
    headers = {'Authorization': f'Bearer {access_token}'}
    user_info_response = requests.get(user_info_url, headers=headers)
    user_info_json = user_info_response.json()

    user_id = user_info_json.get('response', {}).get('id', None)
    user_name = user_info_json.get('response', {}).get('name', None)

    # 4. 얻어낸 user id 와 name 을 DB 에 저장한다.
    if user_id and user_name:
        # 여기에 DB에 저장하는 코드 추가
        insert_query = "INSERT INTO user_table (user_id, user_name) VALUES (%s, %s)"
        insert_data = (user_id, user_name)
        
        try:
            cursor.execute(insert_query, insert_data)
            db_connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            db_connection.rollback()


    # 5. 첫 페이지로 redirect 하는데 로그인 쿠키를 설정하고 보내준다.
    response = redirect('/')
    response.set_cookie('userId', user_id)
    return response


@app.route('/memo', methods=['GET'])
def get_memos():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    # TODO: DB 에서 해당 userId 의 메모들을 읽어오도록 아래를 수정한다.
    result = []

    # memos 테이블에 user_id 컬럼이 있다고 가정하고 해당 사용자의 메모를 가져오는 쿼리를 실행
    try:
        query = "SELECT text FROM memos WHERE user_id = %s"
        cursor.execute(query, (userId,))
        memos = cursor.fetchall()  # 모든 메모를 가져옴

        for memo in memos:
            result.append({'text': memo[0]})
    except mysql.connector.Error as err:
        print(f"Error: {err}")

    # memos라는 키 값으로 메모 목록 보내주기
    return jsonify({'memos': result})


@app.route('/memo', methods=['POST'])
def post_new_memo():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    # 클라이언트로부터 JSON 을 받았어야 한다.
    if not request.is_json:
        abort(HTTPStatus.BAD_REQUEST)

    # TODO: 클라이언트로부터 받은 JSON 에서 메모 내용을 추출한 후 DB에 userId 의 메모로 추가한다.
    memo_text = request.json.get('text')
    if not memo_text:
        return jsonify({'error': 'Memo content is required'}), HTTPStatus.BAD_REQUEST

    try:
        # 커서 열기
        cursor = db_connection.cursor()

        # 메모 내용 가져오기
        # memo_text를 가져오는 부분을 여기로 이동
        # (만약 memo_text가 비어 있다면 여기서 에러를 반환하고 함수를 빠져나갈 것이므로 이후의 코드가 실행되지 않음)
        # 그렇지 않은 경우에만 메모 추가 쿼리 실행
        insert_query = "INSERT INTO memos (user_id, text) VALUES (%s, %s)"
        insert_data = (userId, memo_text)
        cursor.execute(insert_query, insert_data)

        # 변경 내용을 커밋
        db_connection.commit()

        # 메모 목록 갱신
        query = "SELECT text FROM memos WHERE user_id = %s"
        cursor.execute(query, (userId,))
        result = [row[0] for row in cursor.fetchall()]  # 결과에서 memo_text만 추출

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        # 오류 발생 시 롤백
        db_connection.rollback()
        return jsonify({'error': 'Internal server error'}), HTTPStatus.INTERNAL_SERVER_ERROR

    finally:
        # 커서 닫기
        cursor.close()

    return jsonify({'message': '메모가 성공적으로 추가되었습니다.', 'memos': result}), HTTPStatus.OK


if __name__ == '__main__':
    app.run('0.0.0.0', port=8000, debug=True)