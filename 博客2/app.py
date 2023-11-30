from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from flask_sqlalchemy import SQLAlchemy as db
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import Form, StringField, PasswordField, validators , SubmitField
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import DataRequired, Length, EqualTo
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'
db_config = {
    'auth_plugin': 'mysql_native_password',
    "host": "localhost",
    'user': 'root',
    'password': 'python',
    'database': 'bkxt',
    'port': 3306,
    'charset': 'utf8'
}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 设置登录路由
# 用户认证表单
class RegistrationForm(FlaskForm):
    username = StringField(label='用户名', validators=[
        DataRequired(message='用户名不能为空'),
        Length(min=3, max=20, message='用户名长度在3~20')
    ])
    password = PasswordField(label='密码', validators=[
        DataRequired(message='密码不能为空'),
        EqualTo('confirm_password', message='两次密码不同！')
    ])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(message='请重新输入密码')])
    submit = SubmitField('注册')
# 用户类
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def get_id(self):
        return self.username
# 定义LoginForm表单类
class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    password = PasswordField('Password', [validators.DataRequired()])
# 动态管理表单
class PostForm(FlaskForm):
    content = StringField('动态内容', validators=[DataRequired()])
    submit = SubmitField('发布')

# 评论表单
class CommentForm(FlaskForm):
    content = StringField('评论内容', validators=[DataRequired()])
    submit = SubmitField('发表')


@login_manager.user_loader
def load_user(user_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM user WHERE id=%s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return User(row[0], row[1])
    return None

@app.context_processor
def get_db():
    conn = mysql.connector.connect(**db_config)
    return {'db': conn}


# 登录界面路由
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User(1, username,password)
        login_user(user)
        flash('登录成功！')
        return redirect(url_for('index'))
    return render_template('login.html')

# 首页路由
@app.route('/index')
@login_required
def index():
    return render_template('index.html')  # 显示首页模板
# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        role = 'normal'
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
        conn.commit()
        cursor.close()
        conn.close()
        flash('您的账户已成功创建！请登录。')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)
# 注销路由
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功注销！')
    return redirect(url_for('index'))

# 点赞功能
def like_post(post_id):
    if current_user.is_authenticated:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO likes (user_id, post_id) VALUES (%s, %s)", (current_user.id, post_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash('点赞成功！')
    else:
        flash('请先登录！')

# 用户搜索功能
def search_user(username):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM user WHERE username LIKE %s", ('%' + username + '%',))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

# 个人主页路由
@app.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first()  # 根据用户名获取用户信息
    if user is None:
        abort(404)  # 用户不存在时返回404错误页面
    posts = user.posts  # 获取用户发布的动态列表
    return render_template('user_profile.html', user=user, posts=posts)

# 动态管理路由
@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    form = PostForm()
    if form.validate_on_submit():
        content = form.content.data
        user_id = current_user.id  # 假设 current_user 是已登录的用户对象
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO posts (user_id, content) VALUES (%s, %s)", (user_id, content))
        conn.commit()
        cursor.close()
        conn.close()
        flash('您的动态已发布！', 'success')
        return redirect(url_for('index'))
    return render_template('post.html', form=form)
# 查看动态路由
def get_post(post_id):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM posts WHERE id=%s", (post_id,))
    post = cursor.fetchone()
    cursor.close()
    return post

def like_post(post_id):
    try:
        if current_user.is_authenticated:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO likes (user_id, post_id) VALUES (%s, %s)", (current_user.id, post_id))
            conn.commit()
    except Exception as e:
        print(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def view_post(post_id):
    post = get_post(post_id)
    if post is None:
        abort(404)
    comments = getattr(post, 'comments', [])
    return render_template('view_post.html', post=post, comments=comments)

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = get_post(post_id)
    if post is None or post.user_id != current_user.id:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        content = form.content.data
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("UPDATE posts SET content=%s WHERE id=%s", (content, post_id))
            conn.commit()
            flash('您的动态已更新！', 'success')
        except Exception as e:
            print(e)
            flash('更新动态失败！', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return redirect(url_for('view_post', post_id=post_id))
    elif request.method == 'GET':
        form.content.data = post.content
    return render_template('edit_post.html', form=form)

# 评论功能路由
@app.route('/post/<int:post_id>/comment', methods=['GET', 'POST'])
@login_required
def comment(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        content = form.content.data
        user_id = current_user.id  # 假设 current_user 是已登录的用户对象
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)",
                       (post_id, user_id, content))
        conn.commit()
        cursor.close()
        conn.close()
        flash('您的评论已发表！', 'success')
        return redirect(url_for('view_post', post_id=post_id))  # 重定向到动态页面，以显示新发表的评论
    return render_template('comment.html', form=form)
# 点赞功能路由
@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like(post_id):
    like_post(post_id)  # 调用点赞功能函数
    return redirect(url_for('view_post', post_id=post_id))  # 点赞后重定向到动态页面
# 动态删除功能路由
@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = get_post(post_id)  # 根据 post_id 获取动态信息，包括内容和发布者信息
    if post is None or post.user_id != current_user.id:  # 只能删除自己发布的动态
        abort(403)  # 权限不足时返回403错误页面
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id=%s", (post_id,))  # 删除动态
    conn.commit()
    cursor.close()
    conn.close()
    flash('您的动态已删除！', 'success')
    return redirect(url_for('index'))  # 删除后重定向到首页
if __name__ == '__main__':
    app.run(debug=True)