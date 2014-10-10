import os
import urllib
import datetime

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import db

import jinja2
import webapp2
import logging

from google.appengine.api import urlfetch
from datetime import datetime

import sched
import json


FACEBOOK_APP_ID = "1461964880758129"
FACEBOOK_APP_SECRET = "fbb97a863bd505ab97959e50ead73754"

GRAPH_API_URL =" https://graph.facebook.com/v2.1"

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)



class User(ndb.Model):
   user_id = ndb.StringProperty(required=True)
   access_token = ndb.StringProperty(required=True)


class Posts(ndb.Model):
    user_id = ndb.StringProperty(required=True)
    access_token = ndb.StringProperty(required=True)
    message = ndb.StringProperty(required=True)
    date_to_post = ndb.DateTimeProperty()
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    status = ndb.StringProperty(default="TBP")


def short_to_long_lived(access_token,self):
    url = "https://graph.facebook.com/oauth/access_token"
    data = {
        "grant_type" : "fb_exchange_token",
        "fb_exchange_token": access_token,
        "client_id" : FACEBOOK_APP_ID,
        "client_secret" : FACEBOOK_APP_SECRET,
        
   }
   form_data = urllib.urlencode(data)
   result = urlfetch.fetch(url=url,payload=form_data,method=urlfetch.POST)
 
   return result.content

def decode_response(str):
   access_token = str.split("&")[0].split("=")[1]
   return {
       "access_token" : access_token,
   }

def write_template(self,template,template_values=None):
   header = JINJA_ENVIRONMENT.get_template('templates/header.html')
   template = JINJA_ENVIRONMENT.get_template('templates/'+template)
 if template_values:
    self.response.write(header.render()+template.render(template_values))
 else:
    self.response.write(header.render()+template.render())





class MainHandler(webapp2.RequestHandler):
    def get(self):
        write_template(self,"main.html")

    def post(self):
        post = Posts()
        post.user_id = self.request.get("fbID")       
        post.message = self.request.get("message")
        post.date_to_post = datetime.strptime(self.request.get("date_to_post"),'%m/%d/%Y %I:%M %p')
        access_token = self.request.get("access_token")
        request = short_to_long_lived(access_token,self)
        request = decode_response(request)
        post.access_token = request["access_token"]
        post.put()

        self.response.write('<script>alert("Post Scheduled");window.location.assign("/")</script>')
        self.response.write(post.access_token)



class ListPostHandler(webapp2.RequestHandler):
    def get(self,id):
        to_be_post = ndb.gql("Select * from Posts "+
            "Where user_id = :1 and status = 'TBP' ",id).bind()
        template_values={
            "posts":to_be_post
        }
        write_template(self,"list.html",template_values)



class PostToFBHandler(webapp2.RequestHandler):
    def post(self):
        data = {
                    "method": "post",
                    "message": self.request.get("message"),
                    "access_token": self.request.get("access_token")
                };
        form_data = urllib.urlencode(data)
        url = GRAPH_API_URL+"/me/feed"
        result = urlfetch.fetch(url=url,payload=form_data,method=urlfetch.POST)
        content = json.loads(result.content)
         

        if(content.get("id")):
           self.response.write('<script>alert("Message posted to facebook.");window.location.assign("/")</script>')
        elif content["error"]["error_user_title"]:
            self.response.write('<script>alert("'+content["error"]["error_user_title"]+'");window.location.assign("/")</script>')
        else:
            self.response.write('<script>alert("An error occured.");window.location.assign("/")</script>')



class ViewHandler(webapp2.RequestHandler):
	def get(self,id):
		template_values = {"id":id}
		template = JINJA_ENVIRONMENT.get_template('templates/view.html')
		self.response.write(template.render(template_values))



class EditPostHandler(webapp2.RequestHandler):
    def get(self,id):
        post = Posts.get_by_id(long(id))
        date = post.date_to_post.strftime("%m/%d/%Y %I:%M %p")
        template_values = {
            "post" : post,
            "date" : date
        }
        write_template(self,"edit.html",template_values)

    def post(self,id):
        post = Posts.get_by_id(long(id))
        post.message = self.request.get("message")
        post.date_to_post = datetime.strptime(self.request.get("date_to_post"),'%m/%d/%Y %I:%M %p')
        post.put()
        self.response.write("<script> alert('Edit Successful.');window.location.assign('/list/"+post.user_id+"')</script>")



class DeleteHandler(webapp2.RequestHandler):
    def get(self,id):
        post = Posts.get_by_id(long(id))
        post.key.delete()
        self.response.write("<script> alert('Edit Successful.');window.location.assign('/list/"+post.user_id+"')</script>")


application = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/view/(.*)', ViewHandler),
    ('/list/(.*)',ListPostHandler),
    ('/edit/(.*)',EditPostHandler),
    ('/delete/(.*)',DeleteHandler)
], debug=True)