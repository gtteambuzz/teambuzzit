from teambuzz import view, UserError, ValidationError, AdminController
from models import User, Project, Group
import logging
from google.appengine.api import taskqueue

class List(AdminController):
    errors = {
        '1': ('success', 'Volunteer deleted'),
        '2': ('success', 'Create background task to clear all flags on all Volunteers'),
    }

    @view('/admin/volunteers/list.html')
    def get(self):
        users = User.all()

        return {
            'volunteers': users,
            'User': User,
        }

# TODO add text/plain encoding header
class ListAsCsv(AdminController):
    def initHeaders(self):
        super(ListAsCsv, self).initHeaders()
        self.response.headers["Content-Type"] = "text/plain"

    @view(None)
    def get(self):
        data = []
        fieldnames = ['email', 'name', 'is_pending', 'project', 'group', 'is_project_coordinator', 'is_group_leader']
        data.append(",".join(fieldnames))

        users = User.all()
        for user in users:
            user_data = user.getData()
            well_encoded_user_data_values = [unicode(v).encode("utf-8") for v in user_data]
            data.append(",".join(well_encoded_user_data_values))

        return "\n".join(data)


class ClearFlagsOnAll(AdminController):
    @view('/admin/volunteers/clear-flags.html')
    def get(self):
        return {}

    @view('/admin/volunteers/clear-flags.html')
    def post(self):
        verification = self.request.get('verification')
        if verification != 'clear all flags':
            raise ValidationError(errors={'verification': 'Insufficient verification'})

        taskqueue.add(url='/tasks/clear-flags-on-all-volunteers')
        return self.redirect('/admin/volunteers', {'error': '2'})

class Index(AdminController):
    errors = {
        '1': ('success', 'Volunteer updated')
    }
    def getVolunteer(self, key):
        user = User.get(key)
        self.throw404If(user is None)
        return user

    @view('/admin/volunteers/index.html')
    def get(self, key):
        user = self.getVolunteer(key)

        return {
            'volunteer': user,
            'User': User,
            'Project': Project,
            'Group': Group,
        }

    @view('/admin/volunteers/index.html')
    def post(self, key):
        user = self.getVolunteer(key)
        user.pending = self.request.get('volunteer[pending]') == "true"
        user.pending_code = self.request.get('volunteer[pending_code]')
        user.email = self.request.get('volunteer[email]')
        user.first_name = self.request.get('volunteer[first_name]')
        user.last_name = self.request.get('volunteer[last_name]')
        user.is_pc = self.request.get('volunteer[is_pc]') == "true"
        user.is_group_leader = self.request.get('volunteer[is_group_leader]') == "true"
        user.phone = self.request.get('volunteer[phone]')

        group_key = self.request.get('volunteer[group]')
        group = Group.get(group_key) if group_key != "" else None
        user.setGroup(group)

        project_key = self.request.get('volunteer[project]')
        project = Project.get(project_key) if project_key != "" else None
        user.setProject(project)

        user.save()
        self.redirect('/admin/volunteers/{}'.format(user.key()), {'error': 1})

class Delete(AdminController):
    def getVolunteer(self, key):
        user = User.get(key)
        self.throw404If(user is None)
        return user

    @view('/admin/volunteers/delete.html')
    def get(self, key):
        return {
            'volunteer': self.getVolunteer(key),
        }

    @view('/admin/projects/delete.html')
    def post(self, key):
        volunteer = self.getVolunteer(key)
        volunteer.delete()
        self.redirect('/admin/volunteers', {'error': '1'})
