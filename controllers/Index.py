from teambuzz import view, Controller

class Index(Controller):
    @view('/index/index.html')
    def get(self):
        return {}

class AboutUs(Controller):
    @view('/index/about-us.html')
    def get(self):
        return {}

class Contact(Controller):
    @view('/index/contact.html')
    def get(self):
        return {}

class Faculty(Controller):
    @view('/index/faculty.html')
    def get(self):
        return {}

class Alumni(Controller):
    @view('/index/alumni.html')
    def get(self):
        return {}
