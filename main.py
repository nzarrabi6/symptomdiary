from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView

from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen,\
    ShaderTransition
from kivy.uix.recycleboxlayout import RecycleBoxLayout

import datetime
from data import Record, Base
from sqlalchemy.orm.exc import NoResultFound

from kivy.config import Config
from kivy.lang import Builder
import sys
from diary_widgets import ErrorPopup
import os.path


Config.set('widgets', 'scroll_timeout', 250)
Config.set('widgets', 'scroll_distance', 5)
Config.write()



class MyCustomScreen(Screen):
    main_container = ObjectProperty()
        
    def add_widget(self, widget, index=0):
        if (self.main_container is None):
            # if we haven't initialized main container yet, then add to the root
            print("Adding widget %s to the root " % widget, file=sys.stderr)
            super(MyCustomScreen, self).add_widget(widget, index)
        else:
            print("Adding widget %s to the main container " % widget, file=sys.stderr)
            
            self.main_container.add_widget(widget, index)



class EntryScreen(MyCustomScreen):
    notes_content = ObjectProperty()
    date = ObjectProperty()
    info_blocks = ListProperty()
    
    def fill_in(self, record):
        self.date.text = record.date_entered.isoformat()
        
        for info_block in self.info_blocks:
            info_block.fill_in(record)



class CalendarScreen(MyCustomScreen):
    pass

 
class SymptomDiaryApp(App):
    engine_path = None
    engine = None
    
    calendar_screen = None
    entry_screen = None
    screen_manager = None

#### This is a global for session management
#### We assume that all processing will be called from the main GUI thread
#### And use a thread-local manager
#### We site it in symptom diary app because we can always get a running app
#### Everyone should call getDBSession to get this session
    __Session = None


 
    def __init__(self, engine_path, **kwargs):
        self.engine_path = engine_path
        super(SymptomDiaryApp, self).__init__(**kwargs)
        self.engine = create_engine(self.engine_path, echo=True)
        Base.metadata.create_all(self.engine)


        session_factory = sessionmaker(bind=self.engine)
        self.__Session = scoped_session(session_factory)
        
        
        
        
    def build(self):
        Builder.load_file('kv/diarywidgets.kv')        
        Builder.load_file('kv/entryedit.kv')        
        Builder.load_file('kv/entrydisplay.kv')
        Builder.load_file('kv/appscreens.kv')
        # initalise the screen manager, add screens and game widget to game screen then return it
        self.screen_manager = ScreenManager(transition = ShaderTransition(duration=0.01))
        self.calendar_screen = CalendarScreen(name='calendar')
        self.entry_screen = EntryScreen(name='entry')
        self.screen_manager.add_widget(self.calendar_screen)
        self.screen_manager.add_widget(self.entry_screen)
 
        return self.screen_manager


    def show_calendar_screen(self):
        self.screen_manager.current = 'calendar'
        
    def getDBSession(self):
        ### This will be a locally managed session
        ### Because we are using scoped_session
        return self.__Session()


    def find_entry_by_date(self, date):
        session = self.getDBSession()
        entryQuery = session.query(Record).filter(Record.date_entered == date)
        try:
            result = entryQuery.one()
        except NoResultFound:
            result = None
        
        return result
        
    def create_entry_by_date(self, date, time, notes):
        # first check if entry does not exist
        print('mooo')

        if (self.find_entry_by_date(date) is None):
            print("Will create entry for ", date)
            new_entry = Record(date_entered = date, notes = notes)
            session = self.getDBSession()
            session.add(new_entry)
            session.commit()
        else:
            popup = ErrorPopup(
                f'Cannot create entry for the date of {date.isoformat()} because one already exists. You can edit it instead'
            )
            popup.open()


        
    def display_entry_by_date(self, date):
        print("Will display entry for: ", date)

        entryScreen = self.screen_manager.get_screen('entry')

        entry = self.find_entry_by_date(date)        

        if (entry is not None):
            entryScreen.fill_in(entry)
            self.screen_manager.current = 'entry'
        else:
            popup = ErrorPopup(f'No entry for the date of {date.isoformat()}')

            popup.open()
        
        
    def getEntryDates(self):
        session = self.__Session()
        return [result.date for result in session.query(Record.date_entered.label('date'))]


def usage():
    print(sys.stderr, "Error in command line arguments. Usage: %s [dbfile]".format(sys.argv[0]))
    sys.exit(1)
    
def main(argv):
    if len(argv) > 1:
        usage()

    if len(argv) == 1:
        db_file = os.path.realpath(argv[0])
    else:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        db_file = f"{script_dir}/data/entries.db"
        
    engine_path = f"sqlite:///{db_file}"
    SymptomDiaryApp(engine_path).run()

    
    
if __name__ == '__main__':
    main(sys.argv[1:])



