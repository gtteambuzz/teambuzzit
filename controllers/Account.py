from teambuzz import view, Controller, UserError, ValidationError
from models import User, Phase

class Index(Controller):
    errors = {
        '787': ('danger', 'Cannot leave project because you\'re in a group'),
    }
    @view('/account/index.html')
    def get(self):
        self.requireUser()
        return {
            'Phase': Phase,
        }

class Confirm(Controller):
    def get(self):
        user = self.request.get("user")
        code = self.request.get("code")

        resp = User.gql("WHERE email = :1 AND pending_code = :2", user, code)
        if resp.count() == 1:
            # toggle this user to active
            the_user = resp.get()
            the_user.confirm()
            the_user.put()
            self.setUser(the_user)
            self.redirect("/account")
        else:
            raise Exception('Invalid pending code received')

class ResetPassword(Controller):
    @view('/account/reset-password.html')
    def get(self):
        # check to see if the code is correct
        email = self.request.get('email')
        user = User.findByEmail(email)
        code = self.request.get("code")

        if user.pending_code != code:
            self.redirect('/account/password-reset-confirm', {'error': 1})

        return {
            'u': user,
            'code': code,
        }

    @view('/account/reset-password.html')
    def post(self):
        key = self.request.get('key')
        user = User.get(key)
        code = self.request.get("code")
        password = self.request.get("password")
        password_match = self.request.get("password_match")

        if password == '':
            raise ValidationError(errors={'password': 'Non-empty password required'})
        if password_match != password:
            raise ValidationError(errors={'password_match': 'Password does not match'})

        user.setPassword(password)
        self.redirect('/sign-in', {'error': 23455})

class Delete(Controller):
    @view('/message.html')
    def get(self):
        self.requireUser()
        self.user.delete()
        self.unsetUser()
        return {'message': 'Accout successfully delete'}
