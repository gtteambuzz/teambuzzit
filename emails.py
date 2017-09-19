from google.appengine.api import mail
from config import JINJA_ENVIRONMENT

class Email:
    def send(self):
        message = mail.EmailMessage()
        message.subject = self.getSubject()
        message.sender = "admin@teambuzz.org"
        message.to = self.getTo()
        message.body = JINJA_ENVIRONMENT.get_template(self.getTemplate().lstrip("/")).render(self.params)
        message.send()

class PasswordResetEmail(Email):
    def __init__(self, user):
        self.params = {'user': user}

    def getTemplate(self):
        return 'emails/password-reset.html'

    def getSubject(self):
        return "TEAM Buzz Password Reset"

    def getTo(self):
        return self.params['user'].email

class ConfirmUserEmail(Email):
    def __init__(self, user):
        self.params = {'user': user}

    def getTemplate(self):
        return 'emails/confirm-user.html'

    def getSubject(self):
        return 'Confirm your TEAMBuzz Account'

    def getTo(self):
        return self.params['user'].email
