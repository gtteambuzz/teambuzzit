from google.appengine.ext import db
from google.appengine.api import mail
from emails import ConfirmUserEmail
from config import ROOT_URL
import logging
import datetime
import md5
import random

class Phase(db.Model):
    name = db.StringProperty()
    start_date = db.DateProperty()
    end_date = db.DateProperty()
    description = db.StringProperty()

    @staticmethod
    def getAllForDate(date):
        return [phase for phase in Phase.all() if phase.start_date <= date and phase.end_date >= date]

    @staticmethod
    def getAllForRightNow():
        return Phase.getAllForDate(datetime.date.today())

    @staticmethod
    def isActive(phase_name):
        return phase_name in Phase.getAllForRightNow()

class Greek(db.Model):
    name = db.StringProperty()

    def isDefault(self):
        return self.name == "Not Affiliated"

class Project(db.Model):
    name = db.StringProperty()
    description = db.StringProperty(multiline=True)
    location = db.StringProperty()
    types = ['Indoor', 'Outdoor', 'Children', 'Fun']
    type_of_work = db.StringProperty(choices = types, default='Fun')
    max_volunteers = db.IntegerProperty()
    spots_taken = db.IntegerProperty(default=0)

    def getForm(self):
        return None

    def isFull(self):
        return self.spots_taken >= self.max_volunteers

    def isAlmostFull(self):
        return self.max_volunteers - self.spots_taken <= 4

    def getSpotsRemaining(self):
        return self.max_volunteers - self.spots_taken

    def getLabelForType(self):
        if self.type_of_work == 'Indoor':
            return 'primary'
        elif self.type_of_work == 'Outdoor':
            return 'success'
        elif self.type_of_work == 'Children':
            return 'default'
        else:
            return 'info'

    def addVolunteer(self):
        self.incrementSpotsTaken(1)

    def removeVolunteer(self):
        self.incrementSpotsTaken(-1)

    def addGroup(self, group):
        self.incrementSpotsTaken(group.slots)

    def removeGroup(self, group):
        self.incrementSpotsTaken(-group.slots)

    @db.transactional
    def incrementSpotsTaken(self, n):
        obj = db.get(self.key())
        final_spots_taken = obj.spots_taken + n
        if final_spots_taken > obj.max_volunteers and obj.spots_taken <= obj.max_volunteers:
            raise OverflowError('Attempting to add {} volunteers, but cannot volunteer more people ({}) than project fits ({})'.format(n, final_spots_taken, obj.max_volunteers))
        self.setSpotsTaken(final_spots_taken)

    @db.transactional
    def setSpotsTaken(self, n, forcefully=False):
        obj = db.get(self.key())
        if n < 0:
            n = 0
        if obj.spots_taken <= obj.max_volunteers:
            if (n > obj.max_volunteers) and not forcefully:
                raise OverflowError('Out of bounds number of spots taken. {} is greater than {}'.format(n, obj.max_volunteers))
        obj.spots_taken = n
        obj.put()

    def getVolunteersEmails(self):
        return ','.join(map(lambda user: user.email, self.volunteers))

    def delete(self):
        for group in self.groups:
            group.setProject(None)

        for volunteer in self.volunteers:
            volunteer.setProject(None)

        super(Project, self).delete()

    @staticmethod
    def getAllTypes():
        return Project.types

class Group(db.Model):
    name = db.StringProperty()
    password = db.StringProperty()
    project = db.ReferenceProperty(Project, collection_name='groups')
    slots = db.IntegerProperty()
    spots_taken = db.IntegerProperty(default=0)
    pending = db.BooleanProperty(default=False)

    def getSpotsTaken(self):
        return self.spots_taken

    def getSpotsRemaining(self):
        return self.slots - self.getSpotsTaken()

    def canJoin(self):
        return self.getSpotsTaken() < self.slots

    def isFull(self):
        return self.getSpotsTaken() == self.slots

    def getMembersEmails(self):
        return ','.join(map(lambda user: user.email, self.members))

    def delete(self):
        if self.project:
            self.project.removeGroup(self)

        for volunteer in self.members:
            volunteer.setGroup(None)
            volunteer.put()

        super(Group, self).delete()

    @db.transactional
    def addMember(self):
        obj = db.get(self.key())
        obj.spots_taken += 1
        obj.put()
        self.spots_taken = obj.spots_taken

    @db.transactional
    def removeMember(self):
        obj = db.get(self.key())
        obj.spots_taken -= 1
        obj.put()
        self.spots_taken = obj.spots_taken

    def setProject(self, project):
        if self.project:
            self.project.removeGroup(self)
        self.project = project
        if self.project:
            self.project.addGroup(self)
        self.put()
        for member in self.members:
            member.setProject(self.project, True)

    @staticmethod
    def create(name, slots, password, autosave=True):
        group = Group()
        group.name = name
        group.slots = slots
        group.password = password
        if autosave:
            group.put()
        return group

class User(db.Model):
    pending = db.BooleanProperty(default=False)
    pending_code = db.StringProperty()
    email = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    first_name = db.StringProperty(required=True)
    last_name = db.StringProperty()
    project = db.ReferenceProperty(Project, collection_name='volunteers')
    is_pc = db.BooleanProperty(default=False)
    is_group_leader = db.BooleanProperty(default=False)
    group = db.ReferenceProperty(Group, collection_name='members')
    phone = db.StringProperty()
    greek_aff = db.ReferenceProperty(Greek)

    def getName(self):
        name = ""
        if self.first_name is not None:
            name += self.first_name
        if self.last_name is not None:
            name += " " + self.last_name
        return name

    def confirm(self):
        self.pending = False
        self.put()

    def setPassword(self, password):
        self.password = User.digestPassword(password)
        self.put()

    def setRandomCode(self, autosave=True):
        r = random.randint(0, 1000000)
        self.pending_code = md5.new(str(r)).hexdigest()
        if autosave:
            self.put()

    def makeGroupLeader(self):
        self.is_group_leader = True
        self.put()

    def setGroup(self, group):
        if self.group:
            self.group.removeMember()
            if self.group.project:
                self.setProject(None, True)
            self.is_group_leader = False
        if self.project:
            self.setProject(None)

        self.group = group

        if self.group:
            self.group.addMember()
            self.setProject(self.group.project, True)

        self.put()

    def setProject(self, project, skip_count_changes=False):
        if self.project and skip_count_changes == False:
            self.project.removeVolunteer()

        self.project = project

        if self.project and skip_count_changes == False:
            self.project.addVolunteer()

        self.put()

    def generateConfirmLink(self):
        self.setRandomCode()
        return "{}confirm?code={}&email={}".format(ROOT_URL, self.pending_code, self.email)

    def generateResetLink(self):
        self.setRandomCode()
        return "{}account/password-reset-confirm?code={}&email={}".format(ROOT_URL, self.pending_code, self.email)

    def getData(self):
        return [
            self.email,
            self.getName(),
            'true' if self.pending else 'false',
            self.project.name if self.project else '',
            self.group.name if self.group else '',
            'true' if self.is_pc else 'false',
            'true' if self.is_group_leader else 'false',
        ]

    def delete(self):
        self.setGroup(None)
        self.setProject(None)
        super(User, self).delete()

    @staticmethod
    def findByEmail(email):
        return User.gql("WHERE email = :1", email).get()

    @staticmethod
    def digestPassword(password):
        return md5.new(password).hexdigest()

    @staticmethod
    def create(name, email, password, project, group, autosave=True):
        digest = User.digestPassword(password)
        user = User(first_name=name, email=email, password=digest)
        if group != None:
            user.setGroup(group)
        elif project != None:
            user.setProject(project)
        user.setRandomCode(autosave)
        if autosave:
            user.put()
        return user
