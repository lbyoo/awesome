#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'lbyoo'

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio,uuid
import os.path,time
import markdown2

from aiohttp import web

from coroweb import get, post
from apis import Page, APIValueError, APIResourceNotFoundError, APIPermissionError

from models import User, Comment, Blog, next_id, Activities, Gifts, UserGifts,Budgets,UserBudgets
from config import configs

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

@asyncio.coroutine
def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = yield from User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

@get('/')
def index(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Activities.findNumber('count(id)',where="state = '1'")
    page = Page(num)
    if num == 0:
        activities = []
    else:
        activities = yield from Activities.findAll(where="state='1'", orderBy='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'activities_index.html',
        'page': page,
        'activities': activities
    }


@get('/blog/{id}')
def get_blog(id):
    blog = yield from Blog.find(id)
    comments = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }

@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

@post('/api/authenticate')
def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = yield from User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r

@get('/manage/')
def manage():
    return 'redirect:/manage/comments'

@get('/manage/comments')
def manage_comments(*, page='1'):
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }

@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }

@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }

@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id
    }

@get('/manage/users')
def manage_users(*, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)
    }

@get('/api/comments')
def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Comment.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, comments=())
    comments = yield from Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, comments=comments)

@post('/api/blogs/{id}/comments')
def api_create_comment(id, request, *, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
    yield from comment.save()
    return comment

@post('/api/comments/{id}/delete')
def api_delete_comments(id, request):
    check_admin(request)
    c = yield from Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    yield from c.remove()
    return dict(id=id)

@get('/api/users')
def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = yield from User.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, users=())
    users = yield from User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return dict(page=p, users=users)

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = yield from User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    yield from user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/api/blogs')
def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)

@get('/api/blogs/{id}')
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog

@post('/api/blogs')
def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    yield from blog.save()
    return blog

@post('/api/blogs/{id}')
def api_update_blog(id, request, *, name, summary, content):
    check_admin(request)
    blog = yield from Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    yield from blog.update()
    return blog

@post('/api/blogs/{id}/delete')
def api_delete_blog(request, *, id):
    check_admin(request)
    blog = yield from Blog.find(id)
    yield from blog.remove()
    return dict(id=id)

@get('/activities/{id}')
def activities(request,*,id):
    user = request.__user__
    activity = yield from Activities.find(id)
    if not activity:
        return {
            '__template__': 'errpage.html',
            'errmsg': '活动id不存在'
        }

    if activity.state != "1":
        return {
            '__template__': 'errpage.html',
            'errmsg': '活动已停止'
        }               

    gifts = yield from Gifts.findAll('activity_id = ?',[id])
    if user is not None:
        user_gifts = yield from UserGifts.findAll('user_id=? and activity_id=?',[user.id,activity.id])
    else:
        user_gifts = []

    return {
        '__template__': 'activities.html',
        'activity':activity,
        'gifts':gifts,
        'user_gifts':user_gifts
    }


@get('/manage/activities')
def manage_activites(request,*,page='1'):
    page_index = get_page_index(page)
    num = yield from Activities.findNumber('count(id)')
    page = Page(num,page_index)
    if num == 0:
        activities = []
    else:
        activities = yield from Activities.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'manage_activities.html',
        'page':page,
        'activities':activities
    }    

@post('/api/activities')
def api_create_activities(request,*,activity_name):
    check_admin(request)
    if not activity_name or not activity_name.strip():
        raise APIValueError('name', 'activity_name cannot be empty.')
    
    activity = Activities(creator=request.__user__.id, creator_name=request.__user__.name, name = activity_name.strip())
    yield from activity.save()
    return activity

@get('/api/activity/{id}/delete')
def api_delete_activity(request,*,id):
    check_admin(request)
    activity = yield from Activities.find(id)
    yield from activity.remove()
    return dict(id=id)


@get('/manage/activity/{activity_id}/gifts')
def manage_activity_gifts(request,*,activity_id):
    activity = yield from Activities.find(activity_id)
    gifts = yield from Gifts.findAll('activity_id = ?',[activity_id])
    return{
        '__template__': 'manage_activity_gifts.html',
        'activity':activity,
        'gifts':gifts
    }

@post('/api/activity/{activity_id}/gift')
def manage_activity_gift(request,*,activity_id,gift_name):
    check_admin(request)
    gift = Gifts(activity_id = activity_id, name = gift_name)
    yield from gift.save()
    return gift

@get('/manage/activity/{activity_id}/gift')
def manage_activity_gift_add(request,*,activity_id):
    activity = yield from Activities.find(activity_id)
    return  {
        '__template__':'manage_activity_gift_add.html',
        'activity':activity
    } 

@post('/manage/activity/{activity_id}/gift')
def manage_activity_gift_add_post(request,*,activity_id,gift_name,image):
    errmsg = ''
    if image.filename.endswith(('jpg','jpeg','png')):
        suffix = os.path.splitext(image.filename)[1]
        fn = uuid.uuid4().hex + suffix
        open('static/img/' + fn, 'wb').write(image.file.read())
        gift = Gifts(activity_id = activity_id,name = gift_name,image = 'static/img/%s'%fn)
        yield from gift.save()
    else:
        errmsg = '图片文件格式不正确'

    activity = yield from Activities.find(activity_id)
    return  {
        '__template__':'manage_activity_gift_add.html',
        'activity':activity,
        'errmsg':errmsg
    }     

@get('/api/gift/{id}/delete')
def api_gift_delete(request,*,id):
    check_admin(request)
    gift = yield from Gifts.find(id)
    yield from gift.remove()
    return gift

@get("/api/activity/{id}/state")
def api_activity_state(request,*,id):
    check_admin(request)
    activity = yield from Activities.find(id)
    if activity.state == '1':
        activity.state = '0'
    else:
        activity.state = '1'
    yield from activity.update()    
    return activity


@get("/api/activity/gift/{id}/select")
def api_activity_gift_select(request,*,id):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')

    gift = yield from Gifts.find(id)
    if gift is None:
        raise APIResourceNotFoundError('Gift')

    activity = yield from Activities.find(gift.activity_id)
    if activity is None:
        raise APIResourceNotFoundError('Activity')
    if activity.state != "1":
        raise APIError('活动已停止')   

    user_gifts = yield from UserGifts.findAll('user_id=? and activity_id = ?',[user.id,activity.id])
    if len(user_gifts) == 0:    
        user_gift = UserGifts(user_id = user.id,activity_id = activity.id,
            gift_id = gift.id,user_name=user.name,gift_name=gift.name,gift_image=gift.image,user_email=user.email)
        yield from user_gift.save()
    else:
        user_gift = user_gifts[0]
        user_gift.gift_id = gift.id
        user_gift.gift_name = gift.name
        user_gift.gift_image = gift.image
        user_gift.user_name = user.name
        user_gift.user_email = user.email
# 
        user_gift.created_at = time.time()
        # print("------------------------------------",time.time())
        yield from user_gift.update()
    

    return dict(gift=gift)  


@get('/manage/activity/{id}/report')
def manage_activity_report(request,*,id):
    user_gifts = yield from UserGifts.findAll('activity_id=?',[id],orderBy='created_at desc')
    activity = yield from Activities.find(id)
    return{
        '__template__':'manage_activity_report.html',
        'user_gifts':user_gifts,
        'activity':activity

    }

#budget 
@get("/manage/budgets")
def manage_budgets(request,*,page=1):
    page_index = get_page_index(page)
    num = yield from Budgets.findNumber('count(id)')
    page = Page(num,page_index)
    if num == 0:
        budgets = []
    else:
        budgets = yield from Budgets.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'manage_budgets.html',
        'page':page,
        'budgets':budgets
    } 


@post('/api/budgets')
def api_budget(request,*,budget_name):
    check_admin(request)
    if not budget_name or not budget_name.strip() :
        raise APIValueError('budget_name')
    budget = Budgets(name=budget_name,creator=request.__user__.id,creator_name=request.__user__.name)
    yield from budget.save()
    return budget

@get('/api/budget/{id}/delete')
def api_delete_budget(request,*,id):
    check_admin(request)
    budget = yield from Budgets.find(id)
    yield from budget.remove()
    return dict(id=id)

@get("/api/budget/{id}/state")
def api_budget_state(request,*,id):
    check_admin(request)
    budget = yield from Budgets.find(id)
    if budget.state == '1':
        budget.state = '0'
    else:
        budget.state = '1'
    yield from budget.update()    
    return budget

@get("/budgets")
def budgets(*,page=1):
    page_index = get_page_index(page)
    num = yield from Budgets.findNumber('count(id)',where="state = '1'")
    page = Page(num,page_index)
    if num == 0:
        budgets = []
    else:
        budgets = yield from Budgets.findAll(where="state='1'", orderBy='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'budgets_index.html',
        'page':page,
        'budgets':budgets
    }

@get("/user/budgets/{id}")
def budget(request,*,id):
    user = request.__user__
    budget = yield from Budgets.find(id)
    if budget.state != "1":
        return {
            '__template__': 'errpage.html',
            'errmsg': '活动已停止'
        }  
    user_budgets = yield from UserBudgets.findAll('user_id=? and budget_id=?',[user.id,id],orderBy="created_at desc")
    
    return {
        '__template__':'budgets.html',
        'user_budgets':user_budgets,
        'budget':budget
    }



@get("/api/budget/{id}/del_user_budget/{user_budget_id}")
def api_del_user_budget(request,*,id,user_budget_id):
    user = request.__user__
    if not user:
        return dict(code=-1,msg="请先登录!")

    budget = yield from Budgets.find(id)
    if not budget:
        return dict(code=-2,msg="预算不存在!")

    if budget.state != "1":
        return dict(code=-3,msg="预算已关闭!")    

    user_budgets = yield from UserBudgets.findAll('id=? and budget_id=? and user_id=?',[user_budget_id,id,user.id])
    if user_budgets:
        yield from user_budgets[0].remove()
    else:
        return dict(code=-4,msg="记录不存在!")    

    return dict(code=0,msg="删除成功")

@post("/api/budget/{id}/add_user_budget")
def api_add_user_budget(request,*,id,budget_type,budget_fee):
    user = request.__user__
    if not user:
        return dict(code=-1,msg="请先登录!")

    budget = yield from Budgets.find(id)
    if not budget:
        return dict(code=-2,msg="预算不存在!")

    if budget.state != "1":
        return dict(code=-3,msg="预算已关闭!")


    user_budget = UserBudgets(user_id=user.id,user_name=user.name,user_email=user.email,
        budget_id=budget.id,budget_type=budget_type,budget_fee=budget_fee)    
    yield from user_budget.save()

    return dict(code=0,msg="保存成功")    
  

@get("/manage/budget/{id}/report")
def manage_budget_report(request,*,id):
    check_admin(request)
    budget = yield from Budgets.find(id)
    user_budgets = yield from UserBudgets.findAll(orderBy="created_at desc")
    return{
        '__template__':'/manage_budget_report.html',
        'user_budgets':user_budgets,
        'budget':budget
    }