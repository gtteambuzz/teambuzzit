from teambuzz import view, UserError, ValidationError, AdminController
from models import Project, Group, User
import logging
from google.appengine.api import taskqueue

class List(AdminController):
    errors = {
        '1': ('success', 'Group deleted'),
        '2': ('success', 'Created background task to delete all groups'),
        '3': ('success', 'Group sizes have been set to their number of members'),
    }

    @view('/admin/groups/list.html')
    def get(self):
        groups = Group.all()
        leaders_emails = ','.join(map(lambda user: user.email, User.all().filter('is_group_leader = ', True).filter('group !=', None)))

        return {
            'groups': groups,
            'Group': Group,
            'leaders_emails': leaders_emails,
        }

class DeleteAll(AdminController):
    @view('/admin/groups/delete-all.html')
    def get(self):
        return {}

    @view('/admin/groups/delete-all.html')
    def post(self):
        verification = self.request.get('verification')
        if verification != 'delete all groups':
            raise ValidationError(errors={'verification': 'Insufficient verification'})

        taskqueue.add(url='/tasks/delete-all-groups')
        return self.redirect('/admin/groups', {'error': '2'})

class CloseRegistration(AdminController):
    @view('/admin/groups/close-registration.html')
    def get(self):
        return {}

    @view('/admin/groups/close-registration.html')
    def post(self):
        verification = self.request.get('verification')
        if verification != 'close group registration':
            raise ValidationError(errors={'verification': 'Insufficient verification'})

        groups = Group.all()
        for group in groups:
            group.slots = group.spots_taken
            group.put()

        return self.redirect('/admin/groups', {'error': '3'})

class Index(AdminController):
    errors = {
        '1': ('success', 'Group created'),
        '2': ('success', 'Group updated'),
    }

    def getGroup(self, key):
        if key == "new":
            return None
        group = Group.get(key)
        self.throw404If(group is None)
        return group

    @view('/admin/groups/index.html')
    def get(self, key):
        group = self.getGroup(key)

        return {
            'key': key,
            'group': group,
            'Project': Project,
        }

    @view('/admin/groups/index.html')
    def post(self, key):
        group = self.getGroup(key)
        if group is None:
            group = Group()

        group.name = self.request.get('group[name]')
        group.password = self.request.get('group[password]')
        try:
            slots = int(self.request.get('group[slots]'))
            if slots <= 0:
                raise ValueError('Below zero')
            group.slots = slots
        except ValueError as e:
            raise ValidationError(errors={'group[slots]': 'Must be an integer number above zero'})

        project_key = self.request.get('group[project]')
        project = Project.get(project_key) if project_key != '' else None
        group.setProject(project)

        group.put()
        error_code = 1 if key == 'new' else 2
        self.redirect('/admin/groups/{}'.format(group.key()), {'error': error_code})

class Delete(AdminController):
    def getGroup(self, key):
        group = Group.get(key)
        self.throw404If(group is None)
        return group

    @view('/admin/groups/delete.html')
    def get(self, key):
        return {
            'group': self.getGroup(key),
        }

    @view('/admin/groups/delete.html')
    def post(self, key):
        group = self.getGroup(key)
        group.delete()
        self.redirect('/admin/groups', {'error': '1'})
