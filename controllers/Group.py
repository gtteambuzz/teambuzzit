from teambuzz import view, UserError, ValidationError, Controller
from models import User, Project, Phase, Greek, Group
import logging

class Init(Controller):
    @view('/groups/index.html')
    def get(self):
        return {
            'groups': Group.all().order('name'),
        }

class Create(Controller):
    # TODO:
    #    send email upon successful creation, encouraging to ask people to join
    #    maybe make an easy link for it? (group and password already filled out...)
    @view('/groups/create.html')
    def get(self):
        name = self.request.get('name')
        email = self.request.get('email')
        user = User.findByEmail(email)
        return {
            'name': name,
            'suggested_user': user,
            'email': email,
            'Project': Project,
            'Greek': Greek,
        }

    @view('/groups/create.html')
    def post(self):
        self.requireUser()

        if self.user.is_pc:
            self.redirect('/groups/create') # this page will show them they cannot be a pc and group leader

        params = {
            'name': self.request.get('name'),
            'slots': self.request.get('slots'),
            'password': self.request.get('password'),
        }
        params = Create.validateGroupParams(params)

        group = Group.create(params['name'], params['slots'], params['password'])
        self.user.setGroup(group)
        self.user.makeGroupLeader()

        self.redirect('/account')

    @staticmethod
    def validateGroupParams(params):
        if len(params['name']) <= 4:
            raise ValidationError(errors={'name': 'Use a name that\'s at least 5 letters or numbers'})

        slots = params['slots']
        if slots != '':
            try:
                slots = int(params['slots'])
            except ValueError as e:
                raise ValidationError(errors={'slots': 'Number of spots must be a whole number'})

            if slots > 30:
                raise ValidationError(errors={'slots': 'Maximum group size is 30'})

            if slots < 0:
                raise ValidationError(errors={'slots': 'Nice try, but no'})

        params['slots'] = slots

        if len(params['password']) <= 4:
            raise ValidationError(errors={'password': 'Use a password that\'s at least 5 letters or numbers'})

        return params


class Edit(Controller):
    @view('/groups/edit.html')
    def get(self):
        self.throw404If(self.user.is_group_leader == False)
        group = self.user.group
        return {
            'name': group.name,
            'slots': group.slots,
            'password': group.password,
        }

    @view('/groups/edit.html')
    def post(self):
        self.throw404If(self.user.is_group_leader == False)
        group = self.user.group
        params = {
            'name': self.request.get('name'),
            'slots': self.request.get('slots'),
            'password': self.request.get('password'),
        }
        logging.info(params)
        params = Create.validateGroupParams(params)
        slots = params['slots']
        if slots != '':
            if slots < group.members.count():
                raise ValidationError(errors={'slots': 'Too few slots for the number of people in your group already'})
            group.slots = slots

        group.name = params['name']
        group.password = params['password']
        group.put()

        self.redirect('/groups/edit', {'errors': 1})

class Join(Controller):
    def getGroup(self):
        gid = self.request.get('id')
        group = Group.get(gid) if gid else None
        return group

    @view('/groups/join.html')
    def get(self):
        group = self.getGroup()
        if group == None:
            return self.error(404)

        return {
            'group': group,
        }

    @view('/groups/join.html')
    def post(self):
        group = self.getGroup()
        if group == None:
            raise Exception('Failed to find group')
        password = self.request.get('password')
        if group.password != password:
            raise ValidationError(errors={'password': 'Invalid password'}, values={'group': group, 'password': password})
        self.user.setGroup(group)
        self.redirect('/account')

class Leave(Controller):
    @view('/groups/leave.html')
    def get(self):
        self.requireUser()
        self.throw404If(self.user.group == None)
        return {}

    @view('/groups/leave.html')
    def post(self):
        self.user.setGroup(None)
        self.redirect('/account')
