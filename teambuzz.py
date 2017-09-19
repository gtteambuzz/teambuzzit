# Big To Do list:
# PC applications
# PC review and approval process
# PC project assignments
# PC UI on My TEAMBuzz (view list of people in project, send them all an email, etc)

# Group creation
# Group management UI

# Admin tools!
# Adding projects
# Shuffling people around


# Specific TODOs
# TODO: send password upon account creation
# TODO: client-side form validation. JQuery will make this easyish
# TODO: change the email address to a correct on on the dev server
# TODO: on failed forms, fill in the old values
# TODO: slots calculation using group slots


import logging
import gmemsess
import md5
import random
import admin
import datetime
import time
import hmac
import hashlib
import json
import urllib

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import users
#from google.appengine.api import mail
from models import *
import config


#CONFIRM_URL = 'http://main.teambuzz.org/confirm'
#CONFIRM_URL = 'http://localhost:8080/confirm'

# ----------------------------------------
# Utility functions
# ----------------------------------------

def updateSessionForLogin(self, username):
    sess = gmemsess.Session(self)
    sess['current_user'] = username
    sess.save()


# ----------------------------------------
# Form validation classes
# ----------------------------------------
class FormValidator:
    message = None
    def verifyArguments(self, a, b):
        """ check if a contains all of the elements in b """
        return set(a) >= set(b)

class UserFormValidator(FormValidator):
    def isValid(self, data):
        if not self.verifyArguments(data.keys(), ["email", "first_name", "last_name", "phone", "greek", "password"]):
            self.message = "Invalid arguments"
            return False

        # make sure the email isn't already being used
        resp = User.gql("WHERE email = :1", data["email"])
        if resp.count() > 0:
            self.message = "Email already in use"
            return False

        # make sure the greek affiliation exists
        resp = Greek.gql("WHERE name = :1", data["greek"])
        if resp.count() == 0:
            self.message = "Error with greek affiliation"
            return False

        return True

    def saveAsPendingUser(self, data):
        greek_aff = Greek.gql("WHERE name=:1", data["greek"]).get()
        pending_user = User(email=data['email'],
                            password=md5.new(data['password']).hexdigest(),
                            first_name = data['first_name'],
                            last_name = data['last_name'],
                            phone = db.PhoneNumber(data['phone']),
                            greek_aff = greek_aff,
                            pending = True)
        pending_user.setRandomCode()
        pending_user.put()
        # ask the user to confirm their account
        ConfirmUserEmail(pending_user).send()
        return pending_user

class GroupFormValidator(FormValidator):
    def isValid(self, data):
        if not self.verifyArguments(data.keys(), ["project", "slots", "passcode", "group_name"]):
            self.message = "Invalid arguments"
            return False
        # make sure project exists
        resp = Project.gql("WHERE name = :1", data["project"])
        if resp.count() < 1:
            self.message = "Project does not exist"
            return False

        # make sure slots is a valid value
        try:
            slots = int(data["slots"])
        except ValueError:
            self.message = "Invalid value for slots"
            return False

        # make sure project has enough open slots
        project = resp.get()
        project.calculateSpots()
        if project.spots_remaining < slots:
            self.message = "Not enough slots for your request"
            return False

        return True

    def createAsPendingGroup(self, data):
        project = Project.gql("WHERE name = :1", data['project']).get()

        new_group = Group(name=data["group_name"],
                          password=data["passcode"],
                          project=project,
                          slots=int(data["slots"]),
                          pending=True)
        new_group.put()
        return new_group

class GroupJoinFormValidator(FormValidator):
    def isValid(self, data):
        if not self.verifyArguments(data.keys(), ["passcode", "group"]):
            self.message = "Invalid arguments"
            return False
        # make sure group exists
        try:
            group = db.get(data['group'])
        except:
            self.message = "That group doesn't exist. How strange."
            return False
        # check the passcode is correct
        if group.password != data["passcode"]:
            self.message = "Incorrect passcode."
            return False
        # check the group has open spots
        if not group.canJoin():
            self.message = "There are no spots remaining in that group."
            return False
        # make sure the group isn't pending
        if group.pending:
            self.message = "This group is pending approval."
            return False
        return True

# ----------------------------------------
# Request Handler classes
# ----------------------------------------
class UserError(Exception):
    pass

class BreakError(Exception):
    pass

class ValidationError(Exception):
    def __init__(self, errors={}, values=None):
        first_message = errors.itervalues().next()
        super(ValidationError, self).__init__(first_message)
        self.errors = errors
        self.values = values

class SignedCookieForgeryException(Exception):
    pass

class Forward:
    def __init__(self, view):
        self.view = view

class SignedCookieSession:

    def __init__(self, session, writer):
        self.writer = writer
        self.session_id = None
        self.expires_at = None
        self.secret = 'ONHSmCFrdktRZI0IeRzERn4LKqautBr2euhB65nW3pBdgMzq2zJ3NcVyrvF2tCy5'
        self.read(session)

    def sign(self, sid, expires, data):
        return "{}:{}:{}:{}".format(sid, self.digest(sid, "{}{}".format(expires, data)), expires, data)

    def unsign(self, sid, unsigned_data):
        signature, expires, data = unsigned_data.split(':')
        if int(expires) < int(time.time()) or self.digest(sid, "{}{}".format(expires, data)) != signature:
            raise SignedCookieForgeryException('Signed cookies forgery')

        return expires, data

    def digest(self, sid, data):
        return hmac.new(self.secret, msg="{}:{}".format(sid, data), digestmod=hashlib.sha256).hexdigest()

    def read(self, session):
        parts = session.split(':', 1)
        if len(parts) < 2:
            return self.setDefaultData()

        self.session_id = parts[0]
        session_string = parts[1]
        if self.session_id == '' or session_string == '':
            return self.setDefaultData()

        expires, data = self.unsign(self.session_id, session_string)
        self.data = self.unstringifyData(data)
        self.expires_at = int(expires)

    def setDefaultData(self):
        self.data = {}
        self.expires_at = int(time.time()) + 60*60*24*7*4*4 # +4 months

    def get(self, key):
        return self.data[key] if key in self.data else None

    def put(self, key, value):
        self.data[key] = value
        self.write()

    def unset(self, key):
        if key in self.data:
            del self.data[key]
        self.write()

    def write(self):
        if self.session_id is None:
            self.session_id = random.randint(0, 16777215)
            self.session_id = 0
        data = self.stringifyData(self.data)
        session_data = self.sign(self.session_id, self.expires_at, data)
        self.writer(self.expires_at, session_data)

    def stringifyData(self, data):
        return json.dumps(data).encode('hex')

    def unstringifyData(self, data):
        return json.loads(data.decode('hex'))

class Controller(webapp.RequestHandler):
    def initialize(self, request, response):
        super(Controller, self).initialize(request, response)
        self.initHeaders()
        self.initFlashes()
        self.initSession()
        self.initUser()
        self.initErrors()

    def initHeaders(self):
        self.response.headers["Pragma"] = "no-cache"
        self.response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, pre-check=0, post-check=0"
        self.response.headers["Expires"] = "Thu, 01 Dec 1994 16:00:00"

    def initFlashes(self):
        self.flashes = []

    def initSession(self):
        cookies = self.request.cookies
        session = cookies['session'] if 'session' in cookies else ''
        def writer(expires_at, session):
            self.response.set_cookie('session', session, expires=datetime.datetime.fromtimestamp(expires_at), path='/')
        try:
            self.session = SignedCookieSession(session, writer)
        except SignedCookieForgeryException as e:
            writer(0, '')

    def initUser(self):
        user_key = self.session.get('user_key') if hasattr(self, 'session') else None
        user = User.get(user_key) if user_key is not None else None
        self.user = user

    def initErrors(self):
        code = self.request.get('error')
        if not code:
            return
        message = self.errors[code] if code in self.errors else 'Unknown error occurred'
        if isinstance(message, str):
            flash_type = 'danger'
        else:
            flash_type = message[0]
            message = message[1]
        self.addFlash(flash_type, message)

    def setupGlobalTemplateValues(self, template_values):
        template_values['user'] = self.getUser()
        template_values['flashes'] = self.flashes
        def url_is(path, strict=False):
            current_path = self.request.path
            prefix_matches = current_path[:len(path)] == path
            return prefix_matches if not strict else current_path == path
        template_values['url_is'] = url_is
        def is_today(year=None, month=None, day=None):
            now = datetime.datetime.today()
            if year is None:
                year = now.year
            if month is None:
                month = now.month
            if day is None:
                day = now.day
            return now.year == year and now.month == month and now.day == day
        template_values['is_today'] = is_today
        def include_static_asset(path):
            return '{}?v={}'.format(path, config.VERSION)
        template_values['include_static_asset'] = include_static_asset
        def get_current_path():
            path = self.request.path
            query = self.request.query_string
            if query:
                path += '?' + query
            return path
        template_values['get_current_path'] = get_current_path
        def make_path(path, params={}, include_domain=False):
            params = dict((k, v) for k, v in params.iteritems() if v)
            query_string = urllib.urlencode(params)
            if len(query_string) > 0:
                path += '?' + query_string
            if include_domain:
                path = self.request.host_url + path
            return path
        template_values['make_path'] = make_path
        template_values['config'] = config

    def flashError(self, message):
        self.addFlash('danger', message)

    def addFlash(self, flash_type, message):
        self.flashes.append((flash_type, message))

    def getUser(self):
        return self.user

    def setUser(self, user):
        user_key = str(user.key())
        self.session.put('user_key', user_key)

    def unsetUser(self):
        self.session.unset('user_key')
        self.user = None

    def requireUser(self):
        if self.user is None:
            self.redirect('/sign-in', {'error': '472'})
            raise BreakError()

    def throw404If(self, condition):
        if condition:
            self.error(404)
            self.response.out.write('404 Not Found')
            raise BreakError()

    def getAllParams(self):
        params = {}
        for arg in self.request.arguments():
            params[arg] = self.request.get(arg)
        return params

    def redirect(self, url, params={}):
        encoded_params = urllib.urlencode(params)
        if len(encoded_params):
            url += '?' + encoded_params
        super(Controller, self).redirect(url)

class AdminController(Controller):
    def initUser(self):
        # limiting users to being admins happens in app.yaml, so there's actually nothing strict about AdminController
        self.user = users.get_current_user()

def view(filename):
    from google.appengine.ext.webapp import template
    def decorate(function):
        def wrapper(self, *args):
            path = filename

            try:
                template_values = {}
                template_values = function(self, *args)

            except ValidationError as e:
                template_values = e.values if e.values != None else self.getAllParams()
                template_values['errors'] = e.errors
                logging.info(template_values['errors'])

            except UserError as e:
                path = 'error.html'
                template_values = {'error': e}

            except BreakError as e:
                return # used to break out of controller flow when calling redirect() from child function

            if isinstance(template_values, Forward):
                path = template_values.view

            if isinstance(template_values, dict):
                if 'errors' not in template_values:
                    template_values['errors'] = {}
                if isinstance(self, Controller):
                    self.setupGlobalTemplateValues(template_values);
                template = config.JINJA_ENVIRONMENT.get_template(path.lstrip("/"))
                response = template.render(template_values)

            else:
                response = str(template_values)

            self.response.out.write(response)
        return wrapper
    return decorate

class BeAPC(webapp.RequestHandler):
    # Add questions here and they will automatically be added to the site and the data
    # store
    questions = ["Why do you want to be a PC?",
                 "What kind of work do you want to do?"]

    def formatAppResponse(self):
        # concatenate all the questions and responses into one big string
        app = ""
        for j in range(len(self.questions)):
            resp = self.request.get("q" + str(j+1))
            app += "Question:\n\n"
            app += self.questions[j]
            app += "\n\nResponse:\n\n"
            app += resp
            app += "\n\n" + "-"*20 + "\n\n"
        return app

    @view('beapc.html')
    def get(self):
        """ Displays the PC Application page """

        if not Phase.isActive("pc_apps"):
            raise UserError("Sorry, PC applications are not available.")

        template_values = {'questions': self.questions}

        # check if the user has already submitted an app
        sess = gmemsess.Session(self)
        if 'current_user' in sess:
            the_user = User.gql("WHERE email = :1", sess['current_user']).get()
            if the_user.pc_application is not None:
                return Forward('alreadyapplied.html')

        template_values['greek'] = Greek.all().order("name")
        return template_values

    def postPCAppExistingUser(self):
        validator = UserFormValidator()
        data = self.request.POST
        if validator.isValid(data):
            # submit the PC app
            new_app = PCApplication(response=self.formatAppResponse())
            new_app.put()
            # try to tie the application to their name
            the_user = User.gql("WHERE email = :1", sess['current_user']).get()

            if the_user.pc_application is not None:
                raise UserError("You have already submitted an app")

            the_user.pc_application = new_app
            the_user.put()
            self.redirect("/me")
        else:
            raise UserError(validator.message)

    @view('message.html')
    def postPCAppNewUser(self):
        validator = UserFormValidator()
        data = self.request.POST
        if not validator.isValid(data):
            raise UserError(validator.message)

        # save the application
        new_app = PCApplication(response=self.formatAppResponse(),
                                meeting1=int(data['meeting1']),
                                meeting2=int(data['meeting2']))
        new_app.put()
        user = validator.saveAsPendingUser(data)
        user.pc_application = new_app
        user.put()
        return {
            'title': "Great!",
            'message': "We just sent you an email with the link to confirm your email address."
        }

    def post(self):
        """ Submits the PC application """
        if not Phase.isActive("pc_apps"):
            raise UserError("Sorry, PC applications are not available.")

        # two different behaviors, depending on whether the user is logged in
        sess=gmemsess.Session(self)
        if 'current_user' in sess:
            self.postPCAppExistingUser()
        else:
            self.postPCAppNewUser()

from controllers import Index, Projects, SignIn, SignUp, Account, Group, Tasks
from controllers.admin import Index as AdminIndex
from controllers.admin import Projects as AdminProjects
from controllers.admin import Volunteers as AdminVolunteers
from controllers.admin import Groups as AdminGroups

handlers = [
    ('/', Index.Index),
    ('/contact', Index.Contact),
    ('/about-us', Index.AboutUs),
    ('/faculty', Index.Faculty),
    ('/alumni', Index.Alumni),
    ('/projects/?', Projects.Index),
    ('/projects/join', Projects.Join),
    ('/projects/leave', Projects.Leave),
    ('/beapc', BeAPC),
    ('/groups/?', Group.Init),
    ('/groups/create', Group.Create),
    ('/groups/join', Group.Join),
    ('/groups/leave', Group.Leave),
    ('/groups/edit', Group.Edit),
    ('/sign-up', SignUp.Index),
    ('/sign-in', SignIn.Index),
    ('/sign-in/out', SignIn.Out),
    ('/sign-in/forgot-password', SignIn.RequestPasswordReset),
    ('/account/?', Account.Index),
    ('/account/confirm', Account.Confirm),
    ('/account/password-reset-confirm', Account.ResetPassword),
    ('/account/delete', Account.Delete),
    ('/admin/?', AdminIndex.Index),
    ('/admin/init', AdminIndex.Init),
    ('/admin/stats', AdminIndex.Stats),
    ('/admin/recalculate', AdminIndex.Recalculate),
    ('/admin/volunteers/?', AdminVolunteers.List),
    ('/admin/volunteers.csv', AdminVolunteers.ListAsCsv),
    ('/admin/volunteers/clear-flags', AdminVolunteers.ClearFlagsOnAll),
    ('/admin/volunteers/([^/]+)', AdminVolunteers.Index),
    ('/admin/volunteers/([^/]+)/delete', AdminVolunteers.Delete),
    ('/admin/projects/?', AdminProjects.List),
    ('/admin/projects/delete', AdminProjects.DeleteAll),
    ('/admin/projects/([^/]+)', AdminProjects.Index),
    ('/admin/projects/([^/]+)/delete', AdminProjects.Delete),
    ('/admin/groups/?', AdminGroups.List),
    ('/admin/groups/delete', AdminGroups.DeleteAll),
    ('/admin/groups/close-registration', AdminGroups.CloseRegistration),
    ('/admin/groups/([^/]+)', AdminGroups.Index),
    ('/admin/groups/([^/]+)/delete', AdminGroups.Delete),
    ('/tasks/delete-all-groups', Tasks.DeleteAllGroups),
    ('/tasks/delete-all-projects', Tasks.DeleteAllProjects),
    ('/tasks/clear-flags-on-all-volunteers', Tasks.ClearFlagsOnAllVolunteers),
]

application = webapp.WSGIApplication(handlers, debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
