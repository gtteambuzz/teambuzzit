from teambuzz import view, UserError, ValidationError, AdminController
from models import Project, Phase
import logging
from google.appengine.api import taskqueue

class List(AdminController):
    errors = {
        '1': ('success', 'Project deleted'),
        '2': ('success', 'Created background task to delete all project'),
    }

    @view('/admin/projects/list.html')
    def get(self):
        projects = Project.all()

        return {
            'projects': projects,
            'Project': Project,
        }

class DeleteAll(AdminController):
    @view('/admin/projects/delete-all.html')
    def get(self):
        return {}

    @view('/admin/projects/delete-all.html')
    def post(self):
        verification = self.request.get('verification')
        if verification != 'delete all projects':
            raise ValidationError(errors={'verification': 'Insufficient verification'})

        taskqueue.add(url='/tasks/delete-all-projects')
        return self.redirect('/admin/projects', {'error': '2'})

class Index(AdminController):
    errors = {
        '1': ('success', 'Project created'),
        '2': ('success', 'Project updated'),
    }

    def getProject(self, key):
        if key == "new":
            return None
        project = Project.get(key)
        self.throw404If(project is None)
        return project

    @view('/admin/projects/index.html')
    def get(self, key):
        project = self.getProject(key)

        return {
            'key': key,
            'project': project,
            'Project': Project,
        }

    @view('/admin/projects/index.html')
    def post(self, key):
        project = self.getProject(key)
        if project is None:
            project = Project()

        project.name = self.request.get('project[name]')
        project.description = self.request.get('project[description]')
        project.location = self.request.get('project[location]')
        project.type_of_work = self.request.get('project[type_of_work]')
        try:
            spots = int(self.request.get('project[max_volunteers]'))
            if spots <= 0:
                raise ValueError('Below zero')
            project.max_volunteers = spots
        except ValueError as e:
            raise ValidationError(errors={'project[max_volunteers]': 'Must be an integer number above zero'})

        project.put()

        error_code = 1 if key == 'new' else 2
        self.redirect('/admin/projects/{}'.format(project.key()), {'error': error_code})

class Delete(AdminController):
    def getProject(self, key):
        project = Project.get(key)
        self.throw404If(project is None)
        return project

    @view('/admin/projects/delete.html')
    def get(self, key):
        return {
            'project': self.getProject(key),
        }

    @view('/admin/projects/delete.html')
    def post(self, key):
        project = self.getProject(key)
        project.delete()
        self.redirect('/admin/projects', {'error': '1'})
