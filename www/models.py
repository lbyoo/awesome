#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Models for user, blog, comment.
'''



import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)

class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(default=time.time)

class Activities(Model):
    __table__ = 'activities'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    name = StringField(ddl='varchar(50)')
    begin_date = FloatField(default=time.time)
    end_date = FloatField(default=time.time)
    created_at = FloatField(default=time.time)
    creator = StringField(ddl='varchar(50)')
    state = StringField(ddl='varchar(10)', default='1')
    creator_name = StringField(ddl='varchar(50)')

class Gifts(Model):
    __table__ = 'gifts'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    activity_id = StringField(ddl='varchar(50)')
    created_at = FloatField(default=time.time)


class UserGifts(Model):
    __table__ = 'user_gifts'
    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_email = StringField(ddl='varchar(50)')
    activity_id = StringField(ddl='varchar(50)')
    gift_id = StringField(ddl='varchar(50)')
    gift_name = StringField(ddl='varchar(50)')
    gift_image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)

#budget 
class Budgets(Model):
    __table__ = 'budgets'
    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    name = StringField(ddl='varchar(50)')
    creator = StringField(ddl='varchar(50)')
    creator_name = StringField(ddl='varchar(50)')
    state = StringField(ddl='varchar(10)', default='1')
    created_at = FloatField(default=time.time)

class UserBudgets(Model):
    __table__ = 'user_budgets'
    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_email = StringField(ddl='varchar(50)')
    budget_id = StringField(ddl='varchar(50)')
    budget_type = StringField(ddl='varchar(50)')
    budget_fee = FloatField(default=0)
    created_at = FloatField(default=time.time)
    
