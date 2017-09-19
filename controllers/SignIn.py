from teambuzz import view, Controller, ValidationError
from emails import PasswordResetEmail
import logging
from models import User

class Index(Controller):
    errors = {
        '472': ('info', 'Sign in first, before accessing that page'),
        '2345': ('info', 'Sign in to your account before creating a group'),
        '2346': ('info', 'Sign in to your account before joining a group'),
        '9202': 'Account with that email already exists, but needs to be verified. Check your inbox.',
        '4482': 'Account with that email already exists. Try signing in instead.',
        '23455': ('info', 'Password reset successfully! Please log in again to view your account.'),
    }

    @view('/sign-in/index.html')
    def get(self):
        return {
            'redirect': self.request.get('redirect'),
            'email': self.request.get('email'),
        }

    @view('/sign-in/index.html')
    def post(self):
        email = self.request.get('email')
        password = self.request.get('password')

        logging.info("Trying to login {}".format(email))
        user = User.findByEmail(email)

        if user is None:
            raise ValidationError(errors={'email': "No user with that email"}, values=self.getAllParams())
            return {'message': "No account for that email", 'email': email}
        elif user.password != User.digestPassword(password):
            raise ValidationError(errors={'password': "Wrong password"}, values=self.getAllParams())
        elif user.pending == True:
            raise ValidationError(errors={'email': "Pending account confirmation. Check your inbox."}, values=self.getAllParams())

        self.setUser(user)
        redirect = self.request.get('redirect')
        self.redirect(redirect if redirect else '/account')

class Out(Controller):
    def get(self):
        if self.user:
            self.unsetUser()
        self.redirect('/')

class RequestPasswordReset(Controller):
    @view('/sign-in/request-password-reset.html')
    def get(self):
        return {
            'redirect': self.request.get('redirect')
        }

    @view('/sign-in/request-password-reset.html')
    def post(self):
        email = self.request.get('email')
        logging.info('Trying to reset {}'.format(email))

        user = User.findByEmail(email)
        if not user:
            raise ValidationError(errors={'email': "No user with that email. Try another?"})

        PasswordResetEmail(user).send()
        self.addFlash('success', 'Password reset email sent')
        return {}
