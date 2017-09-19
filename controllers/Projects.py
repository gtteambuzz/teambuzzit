from teambuzz import view, Controller, UserError, ValidationError
from models import Project, Phase
from google.appengine.ext import db
import logging

class Index(Controller):
    errors = {
        '786': "Cannot join another project without leaving your current one",
        '787': "Must leave your group before changing your project",
        '489': "Not enough spots available in that project",
    }

    @view('/projects/index.html')
    def get(self):
        projects = Project.all()
        return {
            'Project': Project,
            'projects': projects,
        }

class Join(Controller):
    def post(self):
        pid = self.request.get('id')
        project = db.get(pid)
        if project is None:
            raise Exception('Got linked to a project id that does not exist: {}'.format(pid))

        if self.user is None:
            return self.redirect('/sign-up', {'pid': pid})

        if not self.user.is_group_leader:
            if self.user.group:
                return self.redirect('/projects', {'error': '787'})
            elif self.user.project:
                return self.redirect('/projects', {'error': '786'})

        try:
            if self.user.is_group_leader:
                self.user.group.setProject(project)
            else:
                self.user.setProject(project)
        except OverflowError as e:
            return self.redirect('/projects', {'error': '489'})

        self.redirect('/account')

class Leave(Controller):
    @view('/projects/leave.html')
    def get(self):
        self.requireUser()
        self.throw404If(self.user.project == None)
        return {}

    @view('/projects/leave.html')
    def post(self):
        if self.user.group != None and not self.user.is_group_leader:
            return self.redirect('/projects', {'error': '787'})
        if self.user.is_group_leader:
            self.user.group.setProject(None)
        else:
            self.user.setProject(None)
        self.redirect('/account')
