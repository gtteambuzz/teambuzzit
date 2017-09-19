from teambuzz import view, Controller, ValidationError
import logging
from models import User, Project, Greek

class Index(Controller):
    errors = {
        '2345': ('info', 'Sign up for an account before creating a group'),
        '2346': ('info', 'Sign up for an account before joining a group'),
    }

    @view('/sign-up/index.html')
    def get(self):
        email = self.request.get('email')
        pid = self.request.get('pid')
        project = Project.get(pid) if pid else None
        redirect = self.request.get('redirect')

        return {
            'email': email,
            'project': project,
            'Greek': Greek,
            'redirect': redirect,
        }

    @view('/sign-up/index.html')
    def post(self):
        waiver = self.request.get('waiver')
        if waiver != 'yes':
            raise ValidationError(errors={'waiver': 'You must accept the waiver'})

        name = self.request.get('name')

        email = self.request.get('email')
        user = User.findByEmail(email)
        if user != None:
            code = 9202 if user.pending == True else 4482
            return self.redirect('/sign-in', {'error': code, 'email': email})

        password = self.request.get('password')
        if len(password) < 5:
            raise ValidationError(errors={'password': 'Must be at least 5 characters'})

        pid = self.request.get('pid')
        project = Project.get(pid) if pid else None

        gid = self.request.get('group[key]')
        group = Group.get(gid) if gid else None
        group_code = self.request.get('group[password]')
        group = group if group and group.password == group_code else None

        user = User.create(name, email, password, project, group)
        self.setUser(user)

        redirect = self.request.get('redirect')
        redirect = redirect if redirect else '/account'
        self.redirect(redirect)
