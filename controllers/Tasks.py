from teambuzz import view, UserError, ValidationError, Controller
from models import User, Project, Phase, Greek, Group

class DeleteAllGroups(Controller):
    def post(self):
        groups = Group.all()
        for group in groups:
            group.delete()

class DeleteAllProjects(Controller):
    def post(self):
        projects = Project.all()
        for project in projects:
            project.delete()

class ClearFlagsOnAllVolunteers(Controller):
    def post(self):
        volunteers = User.all()
        for volunteer in volunteers:
            volunteer.is_pc = False
            volunteer.is_group_leader = False
            volunteer.put()
