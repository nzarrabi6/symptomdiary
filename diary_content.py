from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
from kivy.uix.popup import Popup
from main import SymptomDiaryApp
import sys
#from kivy.adapters.listadapter import ListAdapter
from kivy.uix.recycleview import RecycleView


class InfoBlock(BoxLayout):
    record = None    
    main_content = ObjectProperty()
    content_label = StringProperty()
        
    def add_widget(self, widget, index=0):        
        if (self.main_content is None) and not (hasattr(widget, 'shared_content') and (widget.shared_content)):
            self.main_content = widget
            super(InfoBlock, self).add_widget(widget, index)
        elif hasattr(widget, 'shared_content') and (widget.shared_content) :
            super(InfoBlock, self).add_widget(widget, index)
        else:
            self.main_content.add_widget(widget, index)
                                                                          
    def fill_in(self, record):
        self.record = record
        self.update_info()
        
    def _handle_save_finished(self):
        app = SymptomDiaryApp.get_running_app()
        session = app.getDBSession()
        session.commit()        
        self.update_info()
        
    def update_info(self):
        pass
    
    def create_edit_block(self):
        return EditBlock(self.record)

    def edit(self):
        edit_popup = EntryEditPopup()
        edit_popup.add_edit_block(self.create_edit_block())
        edit_popup.bind(on_save_finished = lambda ev: self._handle_save_finished())
        edit_popup.open()



class EditBlock(BoxLayout):
    record = None
    
    def __init__(self, record, **kwargs):
        super(EditBlock, self).__init__(**kwargs)
        self.record = record
        self.fill_in()
        
    def fill_in(self):
        '''Fill in the fields from the current record'''
        raise Exception("The descendant of EditBlock %s must have an fill_in function defined" % self.__class__)
        
    def update_record(self):
        '''Update the record with fields from the block'''
        raise Exception("The descendant of EditBlock %s must have an update_record function defined" % self.__class__)
    
    def validate(self):
        ''' Attempt to validate information in the record before saving it.
            If there are any errors, the overriden method is responsible for displaying them 
            as either popups or other warnings
        ''' 
        return True
            
    def save_validated_content(self):
        self.update_record()


class EditPopup(Popup):
    def __init__(self, **kwargs):
        super(EditPopup, self).__init__(**kwargs)
        self.register_event_type('on_save_finished')
              
    def _handle_save(self):
        if self.validate():
            self.save_validated_content()
            self.dispatch('on_save_finished')
            self.dismiss()
      
    def validate(self):
        return True
      
    def save_validated_content(self):
        raise Exception("Descendant of EditPopup %s must have a save_validated_content method defined." % self.__class__)
    
    def on_save_finished(self):
        pass


    
class EntryEditPopup(EditPopup): 
    edit_block = ObjectProperty()
    
    def add_edit_block(self, edit_block):
        self.edit_block = edit_block
        self.main_content.add_widget(edit_block)

    def validate(self):
        return self.edit_block.validate()
            
    def save_validated_content(self):
        '''Save button was clicked. Attempt to save. If successful, close'''
        self.edit_block.save_validated_content()
            


class ListSummaryInfoBlock(InfoBlock):
    list_manage_button_name = StringProperty()

    def __init__(self, list_manage_button_name="Manage", **kwargs):
        self.list_manage_button_name = list_manage_button_name
        super(ListSummaryInfoBlock, self).__init__(**kwargs);
 
    def on_summary_display(self):
        if (self.summary_display is not None):
            self.update_info()                                   

    def summarize_record(self):
        raise Exception("Must have a summary function for list items defined, in a derived class from ListSummaryInfoBlock")
    
    def update_info(self):
        summary = self.summarize_record()        
        if summary is not None:
            self.summary_display.text = summary
        else:
            self.summary_display.text = "Not recorded"
                   
    def create_list_manage_popup(self):
        raise Exception("Must have a manage popup creation function for list items defined, in a derived class from ListSummaryInfoBlock")
        
    def manage_list_items(self):
        manage_activities_popup = self.create_list_manage_popup()
        manage_activities_popup.open()



class ListManagePopup(Popup):
    record = None
    list_content = ObjectProperty()
    item_class = None

    def __init__(self, record, **kwargs):
        super(ListManagePopup, self).__init__(**kwargs)
        self.record = record
        self._fill_in()

    def on_list_content(self, instance, v):
        self.list_content.data = self.find_all_items()

    def _fill_in(self):
        if (self.list_content is not None):
            self.list_content.data = self.find_all_items()

    def find_all_items(self):
        if (self.item_class is None):
            raise Exception("Item class not defined in ListManagePopup. "
                            + "It must be defined as part of init, "
                            + " before the parent constructor call")
        app = SymptomDiaryApp.get_running_app()
        session = app.getDBSession()
        return session.query(self.item_class).all()

    def new_list_item(self):
        new_record = self.create_new_record()
        new_site_popup = self.create_edit_popup(new_record)
        new_site_popup.bind(on_save_finished=lambda ev: self._add_new_record(new_record))
        new_site_popup.open()

    def _add_new_record(self, record):
        app = SymptomDiaryApp.get_running_app()
        session = app.getDBSession()
        session.add(record)
        session.flush()
        self._fill_in()

    def edit_selected_item(self):
        popup = self.create_edit_popup(self.list_content.data[self.list_content.layout_manager.selected_nodes[0]])
        popup.bind(on_dismiss=self.edit_finished)
        popup.open()

    def edit_finished(self, edit_popup):
        self.list_content.refresh_from_data()
        return False

    def cancel_edits(self):
        app = SymptomDiaryApp.get_running_app()
        session = app.getDBSession()
        session.rollback()
        self.dismiss()

    def save_edits(self):
        app = SymptomDiaryApp.get_running_app()
        session = app.getDBSession()
        session.commit()
        self.dismiss()

    def create_edit_panel(self, record):
        raise Exception("create_edit_panel must be defined in class %s, a descendant of ListManagePopup" % self.__class__)

    def create_new_record(self):
        raise Exception("create_new_record must be defined in class %s, a descendant of ListManagePopup" % self.__class__)

    def create_edit_popup(self, record):
        popup = EntryEditPopup()
        panel = self.create_edit_panel(record)
        entry_edit_block = ListManagerEditBlock()
        entry_edit_block.add_edit_panel(panel)
        popup.add_edit_block(entry_edit_block)
        return popup

class ListManagerEditBlock(BoxLayout):
    active = BooleanProperty(True)
    main_edit_panel = None
            
    @staticmethod
    def is_alnum_phrase(phr):
        '''A helper to check for phrases suitable for DB: must be alnum + spaces, and not empty'''
        return ( not(phr.isspace()) 
                 and all(c.isalnum() or (c in [" ", "-"]) for c in phr) )
            
    def add_edit_panel(self, edit_panel):
        self.main_edit_panel = edit_panel
        self.main_content.add_widget(self.main_edit_panel)
        self.fill_in()

    def create_new_record(self):
        '''Create a completely new, blank record, that can be used for editing and adding it'''
        return self.main_edit_panel.create_new_record()
                
    def fill_in(self):
        '''Fill in the fields from the current record'''
        if (self.main_edit_panel.record is not None):
            self.active = self.main_edit_panel.record.active
        self.main_edit_panel.fill_in()
        
    def save_validated_content(self):
        '''Save the current record. Assumes that validation has been called already, in the EntryEditPopup'''
        self._update_record_from_fields()
        
    def _update_record_from_fields(self):
        '''Update the record with fields from the block'''
        self.main_edit_panel.record.active = self.active
        self.main_edit_panel._update_record_from_fields()
    
    def validate(self):
        ''' Attempt to validate information in the record before saving it.
            If there are any errors, the overriden method is responsible for displaying them 
            as either popups or other warnings
        ''' 
        return self.main_edit_panel.validate()
