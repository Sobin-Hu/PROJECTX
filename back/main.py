from flask import Flask, request, Response
from waitress import serve
import json
import logging

from dao import userDAO
from models import db
from spider import result
from ai import ai_get_history, ai_get_keywords, ai_delete_history

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/user_db?charset=utf8mb4' #mysql+pymysql://用户名:密码@主机/数据库名
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db.init_app(app)

# 配置日志格式
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
    handlers=[logging.StreamHandler()]
)

# 添加请求日志中间件
@app.before_request
def log_request():
    app.logger.debug('Request: %s %s', request.method, request.path)

@app.after_request
def log_response(response):
    app.logger.debug('Response: %s', response.status_code)
    return response

# 统一JSON响应格式
def json_response(code=200, message="操作成功", result=None, reason=None):
    # 构建响应数据字典，确保包含所有四个字段
    response_data = {
        'code': code,
        'message': message,
        'result': result,
        'reason': reason
    }
    # 直接使用code参数作为HTTP状态码
    status_code = code
    # 序列化为JSON字符串，确保中文正常显示
    json_str = json.dumps(response_data, ensure_ascii=False, indent=2)
    # 返回Response对象
    return Response(json_str, mimetype='application/json', status=status_code)

# 查询历史记录数
@app.route('/historycount/<string:username>', methods=['GET'], strict_slashes=False)
def get_history_count(username):
    if not userDAO.check_username(username):
        res = userDAO.get_history_count(username)
        print(res)
        return json_response(message="查询成功",result=res)
    else:
        return json_response(code=404, message="查询失败",reason="用户不存在")

# 查询历史记录
@app.route('/history/<string:session_id>', methods=['GET'], strict_slashes=False)
def get__history(session_id):
    username, cid = session_id.split("_")
    if userDAO.check(username, cid):
        res = ai_get_history(session_id)
        return json_response(message="查询成功", result=res)
    else:
        return json_response(code=404, message="查询失败", reason="无此用户或无此会话")
    
# 游客查询
@app.route('/visitor', methods=['GET'], strict_slashes=False)
def visitor():
    nn = userDAO.visitoradd()
    nc = userDAO.newc(f'visitor{nn}')
    print(nn,nc)
    return json_response(message="游客登录成功", result=[nn, nc])

# 查询结果
@app.route('/keywords/<string:session_id>/<string:question>', methods=['GET'], strict_slashes=False)
def get__result(session_id, question):
    keys = ai_get_keywords(session_id, question) #调用AI获取关键词
    res = result(keys) #根据关键词爬取网站，结果以json返回
    print(session_id, question)
    return json_response(message="得到结果", result=res)

# 删除历史记录
@app.route('/delete/<string:session_id>', methods=['GET'], strict_slashes=False)
def delete(session_id):
    username, cid = session_id.split("_")
    if userDAO.check(username, cid):
        ai_delete_history(session_id)
        userDAO.delete_history(session_id)
        return json_response(message="删除成功")
    else:
        return json_response(code=500, message="删除失败", reason="无此会话")

# 注册用户
@app.route('/register/<string:username>/<string:password>', methods=['GET'], strict_slashes=False)
def register(username, password):
    print(username, password)
    if userDAO.check_username(username):
        userDAO.add_user(username, password)
        return json_response(message="注册成功")
    else:
        return json_response(code=500, message="注册失败", reason="用户名已存在或非法")
    
    
# 登录
@app.route('/login/<string:username>/<string:password>', methods=['GET'], strict_slashes=False)
def login(username, password):
    if userDAO.checklog(username, password):
        return json_response(message="登录成功")
    else:
        return json_response(code=500, message="登录失败", reason="用户名或密码错误")
    
    
# 新对话
@app.route('/new/<string:username>', methods=['GET'], strict_slashes=False)
def new(username):
    if not userDAO.check_username(username):
        return json_response(message="创建成功", result=userDAO.newc(username))
    else:
        return json_response(code=500, message="新对话失败", reason="用户不存在")

if __name__ == '__main__':
    # app.run(debug=True)
    # 创建数据库表
    try:
        with app.app_context():
            db.create_all()
            app.logger.info('Database tables created successfully.')
    except Exception as e:
        app.logger.error(f'Error creating database tables: {e}')

    serve(app, host='0.0.0.0', port=8080)
    