#! /usr/bin/python3
# 20210823
##################

### fixed player option(s) - python list
VLC_PLAYER_OPTIONS = ["--no-xlib"]

### image size in each button
BUTTON_ICON_SIZE = 24

### width and height of the starting window
WWIDTH = 640
HHEIGHT = 640

### timeout - needed for getting file to be loaded properly, mainly for urls
TIME_TO_WAIT = 15

### use the headbar instead of let the wm decorate this window
USE_HEADBAR = 0

### hide the window decoration in fullscreen state
USE_HIDE_DECORATION = 0

##################

import sys,os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from gi.repository import Gdk
gi.require_version('GdkX11', '3.0')
from gi.repository import GdkX11, GdkPixbuf
import time
import vlc
import binascii

MRL = ""

OPTIONS = []

PLAYER_OPTS = []

# info dialog
class DialogBox(Gtk.Dialog):
 
    def __init__(self, parent, info):
        Gtk.Dialog.__init__(self, title="Info", transient_for=parent, flags=0)
        self.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
 
        self.set_default_size(150, 100)
        
        label = Gtk.Label(label=info)
 
        box = self.get_content_area()
        box.add(label)
        self.show_all()

###################################

class ApplicationWindow():
    
    def __init__(self):
        #
        self.builder = Gtk.Builder()
        self.builder.add_from_file("gtk3vlcplayer.glade")
        # the main window
        self.window = self.builder.get_object("window")
        self.window.connect("destroy",Gtk.main_quit)
        self.window.connect("delete-event",Gtk.main_quit)
        self.window.connect("key-press-event", self.on_key_press)
        # window icon
        pixbuf = GdkPixbuf.Pixbuf.new_from_file("icons/gtk3vlcplayer.png")
        self.window.set_icon(pixbuf)
        #
        if USE_HEADBAR:
            self.header = Gtk.HeaderBar(title="PyVlc")
            self.header.props.show_close_button = True
            self.window.set_titlebar(self.header)

    
    def on_key_press(self, w, e):
        # press esc to close this window
        if e.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        
        # press o to open the file dialos
        elif e.keyval == Gdk.KEY_o:
            if not self.player.get_fullscreen():
                if self.player.get_fullscreen() != 1:
                    if self.player.get_state() == 3:
                        self.player.pause()
                        # 
                        self.playback_button.set_image(self.play_image)
                    self.on_file_clicked()
        
        # press u to open the url dialog
        elif e.keyval == Gdk.KEY_u:
            if not self.player.get_fullscreen():
                if self.player.get_state() == 3:
                    self.player.pause()
                    # 
                    self.playback_button.set_image(self.play_image)
                self.on_url_typed()
            
        # press f to set/unset fullscreen
        elif e.keyval == Gdk.KEY_f:
            isVisible = self.hbox.get_property("visible")
            if (isVisible):
                    self.hbox.hide()
            else:
                self.hbox.show()
            
            if USE_HIDE_DECORATION:
                self.window.set_decorated(not self.window.get_decorated())
            #
            self.player.toggle_fullscreen()
        
        # press space to toggle play/pause
        elif e.keyval == Gdk.KEY_space:
            self.on_toggle_player_playback()
        
        # audio track switch
        elif e.keyval == Gdk.KEY_a:
            if not self.player.get_fullscreen():
                self.audio_track = self.player.audio_get_track()
                self.on_audio_track(self.audio_track)
        
        # subtitle track switch
        elif e.keyval == Gdk.KEY_s:
            if not self.player.get_fullscreen():
                self.sub_track = self.player.video_get_spu()
                self.on_sub_track(self.sub_track)
        
        # help dialog
        elif e.keyval == Gdk.KEY_h:
            if not self.player.get_fullscreen():
                self.on_help()
        
        # info dialog
        elif e.keyval == Gdk.KEY_i:
            if not self.player.get_fullscreen():
                ret = self.get_info(self.player.get_media())
                self.on_info(ret)
    
    #
    def on_audio_track(self, data):
        dialog = DialogAudioSub(self.window, self.audio_tracks_list, data, "Choose a different audio track:")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_audio = dialog.get_result()
            self.player.audio_set_track(new_audio)
        dialog.destroy()
    
    #
    def on_sub_track(self, data):
        dialog = DialogAudioSub(self.window, self.subs_tracks_list, data, "Choose a different subtitle track:")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_sub = dialog.get_result()
            self.player.video_set_spu(new_sub)
        dialog.destroy()
    
    #
    def _otherStatus(self, n):
        if n == 1:
            msg = "Skipped"
        elif n == 2:
            msg = "Failed"
        elif n == 3:
            msg = "Timeout"
        # do not quit on errors if it is an url or a dvb device
        if MRL[0:7] not in ["http://", "HTTP://", "https:/", "HTTPS:/", "dvb-t:/"]:
            dialog = DialogY(self.window, "Info", "Error: {}.".format(msg))
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                Gtk.main_quit()
                sys.exit()
    
    #
    def set_options(self, m):
        for opt in OPTIONS:
            m.add_option(opt)
            time.sleep(1)
    
    
    # get some infos from the media
    def get_info(self, m):
        tracks = tuple(m.tracks_get())
        v_codec = ""
        v_fourcc = ""
        v_width = 0
        v_height = 0
        a_codec = ""
        a_channels = 0
        m_duration = 0
        m_duration_temp = m.get_duration()/1000
        if m_duration_temp > 0:
            m, s = divmod(m_duration_temp, 60)
            h, m = divmod(m, 60)
            m_duration = "{0}:{1}:{2}".format(int(h),int(m),round(s,2))
        #
        try:
            for trk in list(tracks):
                if trk.type == 1:
                    codec = trk.codec
                    v_codec = binascii.unhexlify(hex(codec)[2:]).decode()[::-1]
                    fourcc = trk.original_fourcc
                    v_fourcc = binascii.unhexlify(hex(fourcc)[2:]).decode()[::-1]
                    v_width = trk.video.contents.width
                    v_height = trk.video.contents.height
                elif trk.type == 0:
                    codec = trk.codec
                    a_codec = binascii.unhexlify(hex(codec)[2:]).decode()[::-1]
                    a_channels = trk.audio.contents.channels
            #
            to_return ="""
   Video codec = {0}   
   Video fourcc = {1}   
   Video width = {2}   
   Video height = {3}   
   Video lenght = {4}   
   Audio codec = {5}   
   Audio channels = {6}
   """.format(v_codec,v_fourcc,v_width,v_height,m_duration,a_codec,a_channels)
            
            return to_return
        #
        except:
            return "\n       Nothing       \n"
    
    
    def setup_objects_and_events(self):
        ###### player
        PLAYER_OPTS.extend(VLC_PLAYER_OPTIONS)
        self.vlcInstance = vlc.Instance(PLAYER_OPTS)
        try:
            self.player = self.vlcInstance.media_player_new()
        except AttributeError as AE:
            dialog = DialogBox(None, AE)
            dialog.run()
            dialog.destroy()
            Gtk.main_quit()
            sys.exit()
        
        m = self.vlcInstance.media_new(str(MRL))
        
        # 
        if OPTIONS:
            self.set_options(m)
        
        self.player.set_media(m)
        #
        self.player.video_set_key_input(False)
        self.player.video_set_mouse_input(False)
        #
        # Start the parser
        m.parse_with_options(0,1000)
        mTray = 0
        time.sleep(1)
        #
        while True:
            # done
            if m.get_parsed_status() == 4:
                break
            # skipped
            elif m.get_parsed_status() == 1:
                self._otherStatus(1)
                break
            # failed
            elif m.get_parsed_status() == 2:
                self._otherStatus(2)
                break
            # timeout
            elif m.get_parsed_status() == 3:
                self._otherStatus(3)
                break
            else:
                mTray += 1
                if mTray == 5:
                    dialog = DialogY(self.window, "Info", "The media is taking too long.")
                    response = dialog.run()
                    if response == Gtk.ResponseType.OK:
                        Gtk.main_quit()
                        sys.exit()
                time.sleep(1)
        m.parse_stop()
        # set the title of the window
        if USE_HEADBAR:
            self.header.set_title(os.path.basename(str(MRL)))
        else:
            self.window.set_title(os.path.basename(str(MRL)))
        
        #####################
        ###### the widgets
        ### the box
        self.hbox = self.builder.get_object("hbox")
        #
        try:
            pixbuf = Gtk.IconTheme.get_default().load_icon("media-playback-start", BUTTON_ICON_SIZE, 0)
        except:
            try:
                pixbuf = Gtk.IconTheme.get_default().load_icon("gtk-media-play", BUTTON_ICON_SIZE, 0)
            except:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size("icons/none.png", BUTTON_ICON_SIZE, BUTTON_ICON_SIZE)
        self.play_image = Gtk.Image.new_from_pixbuf(pixbuf)
        #
        try:
            pixbuf = Gtk.IconTheme.get_default().load_icon("media-playback-pause", BUTTON_ICON_SIZE, 0)
        except:
            try:
                pixbuf = Gtk.IconTheme.get_default().load_icon("gtk-media-pause", BUTTON_ICON_SIZE, 0)
            except:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size("icons/none.png", BUTTON_ICON_SIZE, BUTTON_ICON_SIZE)
        self.pause_image = Gtk.Image.new_from_pixbuf(pixbuf)
        #
        try:
            pixbuf = Gtk.IconTheme.get_default().load_icon("media-playback-stop", BUTTON_ICON_SIZE, 0)
        except:
            try:
                pixbuf = Gtk.IconTheme.get_default().load_icon("gtk-media-stop", BUTTON_ICON_SIZE, 0)
            except:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size("icons/none.png", BUTTON_ICON_SIZE, BUTTON_ICON_SIZE)
        self.stop_image = Gtk.Image.new_from_pixbuf(pixbuf)
        #
        self.playback_button = self.builder.get_object("button_play")
        self.playback_button.set_image(self.play_image)
        self.stop_button = self.builder.get_object("button_stop")
        self.stop_button.set_image(self.stop_image)
        self.playback_button.connect("clicked", self.toggle_player_playback)
        self.stop_button.connect("clicked", self.stop_player)
        #
        ### mute/unmute button
        try:
            pixbuf = Gtk.IconTheme.get_default().load_icon("audio-volume-high", BUTTON_ICON_SIZE, 0)
        except:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size("icons/none.png", BUTTON_ICON_SIZE, BUTTON_ICON_SIZE)
        self.unmute_image = Gtk.Image.new_from_pixbuf(pixbuf)
        #
        try:
            pixbuf = Gtk.IconTheme.get_default().load_icon("audio-volume-muted", BUTTON_ICON_SIZE, 0)
        except:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size("icons/none.png", BUTTON_ICON_SIZE, BUTTON_ICON_SIZE)
        self.mute_image = Gtk.Image.new_from_pixbuf(pixbuf)
        #
        self.toggle_mute_btn = self.builder.get_object("button_audio")
        self.toggle_mute_btn.set_image(self.unmute_image)
        self.toggle_mute_btn.connect("clicked", self.toggle_audio_mute)
        #
        ### the drawing area
        self.draw_area = self.builder.get_object("draw_area")
        self.draw_area.set_size_request(WWIDTH,HHEIGHT)
        #
        self.draw_area.connect("realize",self._realized)
        self.draw_area.connect('draw', self.onExposeEvent)
        #
        ### scale
        self.scale = self.builder.get_object("scale")
        self.scale.set_draw_value(False)
        self.scale.connect("button-release-event", self.on_scale_changed)
        self.scale.connect("button-press-event", self.on_scale_changed_left)
        self.scale.connect("change-value", self.on_scale_changed_change)
        self.scale.connect("key-release-event", self.on_scale_changed)
        #
        ### the label and its event box
        self.label_scale = self.builder.get_object("label_scale")
        self.label_scale.set_label("0:00:00")
        label_eventbox = self.builder.get_object("eventbox")
        label_eventbox.set_events(Gdk.EventMask.BUTTON_PRESS_MASK| Gdk.EventMask.POINTER_MOTION_MASK)
        label_eventbox.connect("button-press-event", self.on_pb_click)
        self.label_state = False
        # 
        self.window.show_all()
        #
        self.LEFT_MOUSE_BUTTON = 0
    
    
    def toggle_player_playback(self, widget, data=None):
        self.on_toggle_player_playback()
        
    
    def on_toggle_player_playback(self):
        player_state = self.player.get_state()
        # playing
        if player_state == 3 and self.player.can_pause():
            self.player.pause()
            self.playback_button.set_image(self.play_image)
        # paused
        elif player_state == 4:
            self.player.play()
            self.playback_button.set_image(self.pause_image)
        # error
        if player_state == 7:
            self.playback_button.set_image(self.play_image)
            self.player.stop()
        
    
    def stop_player(self, widget, data=None):
        if self.player.is_playing():
            self.player.stop()
            self.playback_button.set_image(self.play_image)
            self.window.set_title("PyVLC")
    
        
    def toggle_audio_mute(self, w):
        #self.player.audio_toggle_mute()
        a_bool = self.player.audio_get_mute()
        if a_bool == 1:
            self.toggle_mute_btn.set_image(self.unmute_image)
            self.player.audio_set_mute(False)
        elif a_bool == 0:
            self.toggle_mute_btn.set_image(self.mute_image)
            self.player.audio_set_mute(True)
        # elif a_bool == -1:
            # pass
    
    
    # do not update the scale if the mouse button is pressed
    def on_scale_changed_left(self, scale, event):
        if event.button == 1:
            self.LEFT_MOUSE_BUTTON = 1
        
    
    # 
    def on_scale_changed_change(self, scale, scroll_type, scale_value):
        if self.LEFT_MOUSE_BUTTON:
            if self.player.is_seekable():
                if self.movie_lenght > 0:
                    # time passed
                    if not self.label_state:
                        to_play_time = self.movie_lenght * round(scale_value, 5)
                        m, s = divmod(to_play_time, 60)
                        h, m = divmod(m, 60)
                        self.label_scale.set_text('{:d}:{:02d}:{:02d}'.format(int(h), int(m), int(s)))
                    # time remaining
                    else:
                        play_time = self.movie_lenght * (1 - round(scale_value, 5))
                        m, s = divmod(play_time, 60)
                        h, m = divmod(m, 60)
                        self.label_scale.set_text('{:d}:{:02d}:{:02d}'.format(int(h), int(m), int(s)))
    
    
    # scrolling the scale widget by mouse
    def on_scale_changed(self, scale, event):
        # the media is seekable
        if self.player.is_seekable():
            new_value = self.scale.get_value()
            self.player.set_position(new_value)
            self.LEFT_MOUSE_BUTTON = 0
    
    
    # label mouse button clicked
    def on_pb_click(self, w, e, d=None):
        self.label_state = not self.label_state

    
    #
    def newMedia(self):
        pret = self._play()
    
    
    #
    def oldMedia(self):
        self.on_toggle_player_playback()
        
    
    #
    def _realized(self, widget, data=None):
        win_id = widget.get_window().get_xid()
        self.player.set_xwindow(win_id)
        #
        pret = self._play()
        if pret:
            GLib.timeout_add(1000,self.update_pb)
    
    
    #
    def _play(self):
        self.player.play()
        # time.sleep(TIME_TO_WAIT)
        # wait for the video to start playing
        i = 0
        self.movie_lenght = 0
        while i<TIME_TO_WAIT:
            i += 1
            if self.player.is_playing():
                # video duration - for all
                m = self.player.get_media()
                media_duration = m.get_duration()
                self.movie_lenght = media_duration/1000
                # video dimentions
                self.vw, self.vh = self.player.video_get_size()
                # set the correct ratio
                if self.vw and self.vh:
                    video_ratio = round(self.vw/self.vh,2)
                    NEW_WIDTH = int(HHEIGHT*video_ratio)
                    self.window.resize(NEW_WIDTH, HHEIGHT)
                # audio tracks
                self.audio_tracks_list = self.player.audio_get_track_description()
                # subs tracks
                self.subs_tracks_list = self.player.video_get_spu_description()
                break
            else:
                time.sleep(1)
        # 
        CAN_PLAY = self.player.will_play()
        if CAN_PLAY == 0 or CAN_PLAY == False:
            dialog = DialogY(self.window, "Error", "Cannot play this media.")
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                Gtk.main_quit()
                sys.exit()
        self.player.audio_set_mute(False)
        # set the pause image
        if self.player.is_playing():
            self.playback_button.set_image(self.pause_image)
            return 1

    
    # update the scale widget position and label every second
    def update_pb(self):
        # media is ended
        if self.player.get_state() == 6:
            self.playback_button.set_image(self.play_image)
            self.player.stop()
        #
        new_pos = self.player.get_position()
        if self.LEFT_MOUSE_BUTTON == 0:
            self.scale.set_value(new_pos)
            if self.movie_lenght > 0:
                # time remaining
                if self.label_state:
                    to_play_time = self.movie_lenght - self.player.get_time()/1000
                    m, s = divmod(to_play_time, 60)
                    h, m = divmod(m, 60)
                    self.label_scale.set_text('{:d}:{:02d}:{:02d}'.format(int(h), int(m), int(s)))
                # time passed
                else:
                    play_time = self.player.get_time()/1000
                    m, s = divmod(play_time, 60)
                    h, m = divmod(m, 60)
                    self.label_scale.set_text('{:d}:{:02d}:{:02d}'.format(int(h), int(m), int(s)))
        
        # stopped
        if self.player.get_state() == 5:
            self.label_scale.set_text("-:--:--")
        
        return True
        
    
    def onExposeEvent(self, area, context):
        context.scale(area.get_allocated_width(), area.get_allocated_height())    
        context.set_source_rgb(0.0, 0.0, 0.0)
        context.fill() 
        context.paint()
    
    
    def on_url_typed(self):
        dialog = DialogURL(self.window)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_url = dialog.get_result()
            if new_url:
                m = self.vlcInstance.media_new(str(new_url))
                self.set_options(m)
                self.player.set_media(m)
                self.window.set_title(os.path.basename(str(new_url)))
                self.newMedia()
            else:
                self.oldMedia()
        elif response == Gtk.ResponseType.CANCEL:
            self.oldMedia()
        dialog.destroy()
    
    
    def on_file_clicked(self):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a file", parent=self.window, action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            selected_file = dialog.get_filename()
            m = self.vlcInstance.media_new(str(selected_file))
            self.set_options(m)
            self.player.set_media(m)
            self.window.set_title(os.path.basename(str(selected_file)))
            self.newMedia()
        elif response == Gtk.ResponseType.CANCEL:
            self.oldMedia()

        dialog.destroy()

    #
    def on_info(self, data):
        dialog = DialogInfo(self.window, data)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.destroy()
        dialog.destroy()
    
    #
    def on_help(self):
        dialog = DialogHelp(self.window)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.destroy()
        dialog.destroy()
    

###################################

# dialog for choosing among the audio or subtitles tracks
class DialogAudioSub(Gtk.Dialog):
    def __init__(self, parent, track_list, data, label):
        Gtk.Dialog.__init__(self, title="Tracks", transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        self.track_list = track_list
        self.data = data
        self.set_default_size(450, 150)
        
        self.idx = 0
        
        label = Gtk.Label(label=label)
        model = Gtk.ListStore(int, str)
        for item in self.track_list:
            model.append([item[0], item[1].decode()])
        self.combo = Gtk.ComboBox.new_with_model_and_entry(model)
        self.combo.connect("changed", self.on_combo_changed)
        self.combo.set_entry_text_column(1)
        #
        for row in model:
            if row[0] == self.data:
                self.combo.set_active_iter(row.iter)
        #
        box = self.get_content_area()
        box.add(label)
        box.add(self.combo)
        self.show_all()
    
    def on_combo_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            row_id, name = model[tree_iter][:2]
            self.idx = row_id

    def get_result(self):
        return self.idx


# load an url as media
class DialogURL(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, title="URL", transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(450, 100)
        self.connect("response", self.on_response)
        
        self.text = ""
        
        label = Gtk.Label(label="Enter a ner URL:")
        self.entry = Gtk.Entry()

        box = self.get_content_area()
        box.add(label)
        box.add(self.entry)
        self.show_all()

    def on_response(self, w, id):
        self.text = self.entry.get_text()

    def get_result(self):
        return self.text


class DialogY(Gtk.Dialog):
    def __init__(self, parent, title, info):
        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(150, 100)

        label = Gtk.Label(label=info)

        box = self.get_content_area()
        box.add(label)
        self.show_all()


# #### dialog YES/NO
# class DialogYN(Gtk.Dialog):
    # def __init__(self, parent, title, info):
        # Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        # self.add_buttons(
            # Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        # )

        # self.set_default_size(150, 100)

        # label = Gtk.Label(label=info)

        # box = self.get_content_area()
        # box.add(label)
        # self.show_all()


#### info dialog
class DialogInfo(Gtk.Dialog):
    def __init__(self, parent, data):
        Gtk.Dialog.__init__(self, title="Info", transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(150, 100)
        llabel = data
        label = Gtk.Label(label=llabel)

        box = self.get_content_area()
        box.add(label)
        self.show_all()


#### help dialog
class DialogHelp(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, title="Help", transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(150, 100)
        llabel = """
    Space: play/pause
    Esc: quit
    o: play a new file
    u: play a new media from internet
    a: choose a different audio track
    s: choose a different subtitle track    
    f: toggle fullscreen
    i: media info"""
        label = Gtk.Label(label=llabel)

        box = self.get_content_area()
        box.add(label)
        self.show_all()


if __name__ == '__main__':
    if not sys.argv[1:]:
        dialog = DialogBox(None, "Exiting \nMust provide one file.")
        dialog.run()
        dialog.destroy()
        sys.exit(1)
    #
    PLAYER_OPTS_TEMP = []
    if len(sys.argv[1:]) > 1:
        TEMP1 = sys.argv[2].split(":")
        if TEMP1[0] == "media":
            OPTIONS = TEMP1[1:]
        elif TEMP1[0] == "player":
            PLAYER_OPTS_TEMP = TEMP1[1:]
    if len(sys.argv[1:]) > 2:
        TEMP2 = sys.argv[3].split(":")
        if TEMP2[0] == "media":
            OPTIONS = TEMP2[1:]
        elif TEMP2[0] == "player":
            PLAYER_OPTS_TEMP = TEMP2[1:]
    if PLAYER_OPTS_TEMP:
        PLAYER_OPTS = ["--"+item for item in PLAYER_OPTS_TEMP]
    #
    MRL = sys.argv[1]
    window = ApplicationWindow()
    window.setup_objects_and_events()
    Gtk.main()
    window.player.stop()
    window.vlcInstance.release()
