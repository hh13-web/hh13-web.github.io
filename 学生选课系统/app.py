import pymysql
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os

app = Flask("学生选课系统")
CORS(app, resources={r"/*": {"origins": "*"}})

# 修改数据库配置 - 从环境变量读取
DB_CONFIG = {
    "host": os.environ.get('DB_HOST', 'localhost'),
    "user": os.environ.get('DB_USER', 'root'),
    "password": os.environ.get('DB_PASSWORD', '123456'),  # 线上会用环境变量
    "database": os.environ.get('DB_NAME', 'xuanke'),
    "charset": "utf8mb4"
}

# 添加根路径 - 返回前端页面
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')



# 学号自动判断学院
def get_college(sid):
    try:
        num_str = ''.join([c for c in sid if c.isdigit()])
        if not num_str:
            return "未知学院"
        num = int(num_str)
    except (ValueError, TypeError):
        return "未知学院"

    if 0 <= num <= 999:
        return "会计学院"
    elif 1000 <= num <= 1999:
        return "信息工程学院"
    elif 2000 <= num <= 2999:
        return "教育学院"
    else:
        return "其他学院"


# 学生登录接口
@app.route('/api/student/login', methods=['POST'])
def student_login():
    try:
        data = request.get_json()
        sid = data.get("sid")
        pwd = data.get("pwd")
        sname = data.get("sname", "")

        if not sid or not pwd:
            return jsonify({"success": False, "message": "账号或密码不能为空"})

        if not sname:
            return jsonify({"success": False, "message": "请输入姓名"})

        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor()

        college = get_college(sid)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("SELECT sid FROM students WHERE sid=%s", (sid,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE students SET sname=%s, pwd=%s, college=%s, login_time=%s, login_count=login_count+1
                WHERE sid=%s
            """, (sname, pwd, college, now, sid))
            db.commit()
        else:
            cursor.execute("""
                INSERT INTO students(sid, sname, pwd, college, login_time, login_count) 
                VALUES(%s, %s, %s, %s, %s, 1)
            """, (sid, sname, pwd, college, now))
            db.commit()

        cursor.execute("SELECT sid FROM students WHERE sid=%s AND pwd=%s", (sid, pwd))
        res = cursor.fetchone()
        cursor.close()
        db.close()
        return jsonify({"success": bool(res)})
    except Exception as e:
        print(f"学生登录错误: {e}")
        return jsonify({"success": False, "message": str(e)})


# 教师登录接口
@app.route('/api/teacher/login', methods=['POST'])
def teacher_login():
    try:
        data = request.get_json()
        tid = data.get("tid")
        pwd = data.get("pwd")
        tname = data.get("tname", "")

        if not tid or not pwd:
            return jsonify({"success": False, "message": "账号或密码不能为空"})

        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor()

        cursor.execute("SELECT tid FROM teachers WHERE tid=%s", (tid,))
        if not cursor.fetchone() and tname:
            cursor.execute("INSERT INTO teachers(tid, tname, pwd) VALUES(%s, %s, %s)", (tid, tname, pwd))
            db.commit()
        elif tname:
            cursor.execute("UPDATE teachers SET tname=%s WHERE tid=%s", (tname, tid))
            db.commit()

        cursor.execute("SELECT tid FROM teachers WHERE tid=%s AND pwd=%s", (tid, pwd))
        res = cursor.fetchone()
        cursor.close()
        db.close()
        return jsonify({"success": bool(res)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


# 管理员登录接口
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        aid = data.get("aid")
        pwd = data.get("pwd")

        if aid == "a001" and pwd == "123456":
            return jsonify({"success": True})
        return jsonify({"success": False})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


# 获取所有课程
@app.route('/api/courses', methods=['GET'])
def get_courses():
    try:
        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT cid, name, credit, semester, teacher_name FROM courses ORDER BY cid")
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(data)
    except Exception as e:
        print(f"获取课程失败: {e}")
        return jsonify([])


# 获取教师任教的课程
@app.route('/api/teacher/courses/<tid>', methods=['GET'])
def get_teacher_courses(tid):
    try:
        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT cid, name, credit, semester, teacher_name as teacher
            FROM courses WHERE teacher_id = %s ORDER BY cid
        """, (tid,))
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(data)
    except Exception as e:
        print(f"获取教师课程失败: {e}")
        return jsonify([])


# 学生选课
@app.route('/api/select', methods=['POST'])
def select_course():
    try:
        data = request.get_json()
        sid = data.get("sid")
        cid = data.get("cid")

        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor()

        cursor.execute("SELECT * FROM student_selected WHERE sid=%s AND cid=%s", (sid, cid))
        if cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({"ok": False, "message": "已经选过这门课了"})

        cursor.execute("INSERT INTO student_selected(sid, cid) VALUES(%s, %s)", (sid, cid))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({"ok": True, "message": "选课成功"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


# 学生退课
@app.route('/api/unselect', methods=['POST'])
def unselect_course():
    try:
        data = request.get_json()
        sid = data.get("sid")
        cid = data.get("cid")

        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor()
        cursor.execute("DELETE FROM student_selected WHERE sid=%s AND cid=%s", (sid, cid))
        db.commit()
        affected = cursor.rowcount
        cursor.close()
        db.close()

        if affected > 0:
            return jsonify({"ok": True, "message": "退课成功"})
        else:
            return jsonify({"ok": False, "message": "未找到该选课记录"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


# 查看我的已选课程（学生用）
@app.route('/api/my_selected/<sid>', methods=['GET'])
def my_selected(sid):
    try:
        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            SELECT c.cid, c.name, c.credit, c.semester, c.teacher_name AS teacher
            FROM student_selected s JOIN courses c ON s.cid = c.cid WHERE s.sid = %s
        ''', (sid,))
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(data)
    except Exception as e:
        print(f"获取已选课程失败: {e}")
        return jsonify([])


# 查看未选课学生
@app.route('/api/unselected_students', methods=['GET'])
def unselected_students():
    try:
        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor(pymysql.cursors.DictCursor)
        cursor.execute('''
            SELECT sid, sname, college FROM students 
            WHERE sid NOT IN (SELECT DISTINCT sid FROM student_selected)
            ORDER BY college, sid
        ''')
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(data)
    except Exception as e:
        print(f"获取未选课学生失败: {e}")
        return jsonify([])


# 添加课程
@app.route('/api/courses', methods=['POST'])
def add_course():
    try:
        data = request.get_json()
        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor()

        cursor.execute("SELECT cid FROM courses WHERE cid=%s", (data["cid"],))
        if cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({"ok": False, "message": "课程编号已存在"})

        cursor.execute("""
            INSERT INTO courses(cid, name, credit, semester, teacher_id, teacher_name) 
            VALUES(%s, %s, 2, %s, %s, %s)
        """, (data["cid"], data["name"], data["semester"], data["teacher_id"], data["teacher_name"]))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({"ok": True, "message": "课程添加成功"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


# 删除课程（管理员用）
@app.route('/api/courses/<cid>', methods=['DELETE'])
def delete_course(cid):
    try:
        db = pymysql.connect(**DB_CONFIG)
        cursor = db.cursor()
        # 先删除该课程的所有选课记录
        cursor.execute("DELETE FROM student_selected WHERE cid=%s", (cid,))
        # 再删除课程
        cursor.execute("DELETE FROM courses WHERE cid=%s", (cid,))
        db.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        db.close()

        if affected_rows > 0:
            return jsonify({"ok": True, "message": "课程删除成功"})
        else:
            return jsonify({"ok": False, "message": "课程不存在"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)