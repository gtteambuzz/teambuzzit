from teambuzz import view, AdminController, Controller
from models import User, Project, Group
from google.appengine.ext import db
import logging

class Index(AdminController):
    errors = {
        '1': ('success', 'Recalculation complete'),
    }

    @view('/admin/index.html')
    def get(self):
        return {}

class Stats(AdminController):
    @view('/admin/stats.html')
    def get(self):
        stats = {}
        stats['volunteers'] = {}
        stats['volunteers']['count'] = 0
        stats['volunteers']['count_has_group'] = 0
        stats['volunteers']['count_no_group'] = 0
        stats['volunteers']['count_has_project'] = 0
        stats['volunteers']['count_no_project'] = 0
        users = User.all()
        for user in users:
            stats['volunteers']['count'] += 1
            if user.group == None:
                stats['volunteers']['count_no_group'] += 1
            else:
                stats['volunteers']['count_has_group'] += 1
            if user.project == None:
                stats['volunteers']['count_no_project'] += 1
            else:
                stats['volunteers']['count_has_project'] += 1
        stats['groups'] = {}
        stats['groups']['count'] = Group.all().count()
        stats['groups']['total_spots'] = sum(map(lambda group: group.slots, Group.all()))
        stats['groups']['spots_taken'] = sum(map(lambda group: group.spots_taken, Group.all()))
        stats['groups']['unused_spots'] = sum(map(lambda group: group.spots_taken, Group.all()))
        stats['projects'] = {}
        stats['projects']['count'] = Project.all().count()
        stats['projects']['total_spots'] = sum(map(lambda project: project.max_volunteers, Project.all()))
        stats['projects']['spots_taken'] = sum(map(lambda project: project.spots_taken, Project.all()))
        stats['projects']['unused_spots'] = stats['projects']['total_spots'] - stats['projects']['spots_taken']
        return stats

class Init(Controller):
    def makeBasicUser(self, username):
        email = username + "@gatech.edu"
        password = username
        user = User.create(username, email, password)
        return user

    def get(self):
        """ init the datastore with some test data.

        assumes the datastore is clear.
        """
        # a basic check to make sure the datastore is clear
        if Greek.all().count() > 0:
            return

        # Create a project
        kitten = Project()
        kitten.name = "Kitten Rescue"
        kitten.max_volunteers = 3
        kitten.location = "All around Atlanta."
        kitten.type_of_work = "Outdoor"
        kitten.description = "We will save kittens from trees all over Atlanta."
        kitten.put()

        soup = Project()
        soup.name = "Soup Making"
        soup.max_volunteers = 5
        soup.description = "You will make delicious soup."
        soup.put()

        huge = Project()
        huge.name = "Huge Project"
        huge.max_volunteers = 20
        huge.description = "This is a darn huge project. With 20 people what CAN'T we do?"
        huge.put()

        # Make a user with a pending PC app
        u = self.makeBasicUser("pending")
        pc_app = PCApplication(response="Here is the sample responses to the questions")
        pc_app.put()
        u.pc_application = pc_app
        u.put()

        # Put a user in the kitten project
        u = self.makeBasicUser("kitten")
        u.project = kitten
        u.put()

        # Create a PC for the soup project
        u = self.makeBasicUser("souppc")
        u.project = soup
        u.is_pc = True
        u.put()

        # Make a group for the HUGE project
        knights_group = Group(name="Knights who say Ni!", password="shrubbery", project=huge, slots=5)
        knights_group.put()

        leader = self.makeBasicUser("leader")
        leader.joinGroup(knights_group)
        leader.is_group_leader = True
        leader.is_pc = True
        leader.put()

        knights = ["lancelot", "gawain", "gallahad", "mordred"]
        for knight in knights:
            k = self.makeBasicUser(knight)
            k.joinGroup(knights_group)
            k.put()

        # Make a full project
        full = Project(name="Full Project",
                       max_volunteers = 5,
                       description = "This was full so quickly...")
        full.put()

        alphabet = "abcdefghijklmnopqrstuvwxyz"
        for j in range(5):
            u = self.makeBasicUser(alphabet[j])
            u.project = full
            u.put()

        # Init the Greek Affliations
        for g_name in GREEK_AFFS:
            g = Greek(name=g_name)
            g.put()

        # Add the possible phases
        phases = [
            ["pc_apps", datetime.date(2014,9,5), datetime.date(2014,10,18)],
            ["group_create", datetime.date(2014,9,19), datetime.date(2014,10,9)],
            ["group_join", datetime.date(2014,9,26), datetime.date(2014,10,9)],
            ["group_registration", datetime.date(2014,9,19), datetime.date(2014,10,9)],
            ["individual_registration", datetime.date(2014,10,10), datetime.date(2014,10,21)]
        ]
        for phase_args in phases:
            phase = Phase(name=phase_args[0], start_date=phase_args[1], end_date=phase_args[2])
            phase.put()

        # Add a group that users can join
        nice_group = Group(name="A nice group for nice people", password="nice!", project=huge, slots=5)
        nice_group.put()

        # Make a user that has no project
        lonely_user = self.makeBasicUser("lonely")
        lonely_user.put()

        return "done"

class Recalculate(Controller):
    @view(None)
    def get(self):
        # fix any references to non-existance objects
        users = User.all()
        for user in users:
            try:
                project = user.project
            except db.ReferencePropertyResolveError as e:
                logging.info('Resolving property resolve error on user.project for {}\'s project {}'.format(user.key(), user._project))
                user.project = None
                user.put()

            try:
                group = user.group
            except db.ReferencePropertyResolveError as e:
                user.group = None
                user.put()

        groups = Group.all()
        for group in groups:
            try:
                project = group.project
            except db.ReferencePropertyResolveError as e:
                group.project = None
                group.put()

        projects = Project.all()
        for project in projects:
            volunteers = project.volunteers.filter('group =', None)
            num_volunteers = volunteers.count()
            groups = project.groups
            num_group_volunteers = sum([group.slots for group in groups])
            spots = num_volunteers + num_group_volunteers
            project.setSpotsTaken(spots, True)

        groups = Group.all()
        for group in groups:
            members = group.members
            num_members = members.count()
            group.spots_taken = num_members
            group.put()

        return self.redirect('/admin', {'error': '1'})
