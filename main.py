from tkinter import Menu, Tk, ttk, messagebox, Text, END, Toplevel, TclError, simpledialog, StringVar
import cloud
import threading
import time
import traceback

win = Tk()
win.title('IESM-Client')
pad_frame = ttk.Frame(win, padding=10)
pad_frame.pack()

class DummyWs:
    def __init__(self) -> None:
        self.data_counter = 0
        self.ws = 'asd'

    def close(self):
        self.ws = None

    def recv(self) -> str:
        time.sleep(0.5)
        self.data_counter += 1
        return f'data: {self.data_counter}\n'

class ChatGUI:
    def __init__(self, 
                 username: str,
                 password: str,
                 room_name: str,
                 project_id: int,
                 encoding: str,
                 connection_type: str) -> None:
        self.username = username
        self.encoding = encoding
        
        self.session_id = cloud.login(username, password) if connection_type == 'Scratch' else None
        print('Loading websocket...')
        self.ws = cloud.Connection(project_id, username, self.session_id, room_name, encoding, connection_type)
        print('Websocket success! Spawning window...')

        self.win = Toplevel(win)
        self.win.title(f'{self.username} на {project_id}/{room_name}')

        self.menubar = Menu(self.win)
        self.win.config(menu=self.menubar)

        self.connection_menu = Menu(self.menubar, tearoff=False)
        self.connection_menu.add_command(
            label='Добавить облачную переменную', 
            command=self.cloud_var_popup,
        )
        self.connection_menu.add_command(
            label='Отключиться', 
            command=self.close_connection,
        )

        self.menubar.add_cascade(label='Соединение', 
                                 menu=self.connection_menu,
                                 underline=0)

        self.pad_frame = ttk.Frame(self.win, padding=10)
        self.pad_frame.pack()

        self.form_frame = ttk.Frame(self.pad_frame, borderwidth=2, relief='groove')
        self.form_frame.pack()

        self.chat_text = Text(self.form_frame, state='disabled', wrap='char')
        self.chat_text.pack()

        self.autoscroll_value = StringVar(value='1')
        self.autoscroll = ttk.Checkbutton(self.form_frame, text='Автопрокрутка', variable=self.autoscroll_value)
        self.autoscroll.pack(anchor='w')

        ttk.Label(self.form_frame, text='Отправить сообщение:').pack(anchor='w')

        self.input_entry = ttk.Entry(self.form_frame)
        self.input_entry.bind('<Return>', self.enter_press)
        self.input_entry.pack(fill='x')

        recv = threading.Thread(target=self.recieve_text)
        recv.start()

    def cloud_var_popup(self):
        out = simpledialog.askstring('Ввод', 'Введите имя облачной переменной (без ☁)')
        if out is None or out.strip() == '': return
        
        out = out.strip()
        if self.ws.add_cloud_var(out):
            self.add_text(f'Успешно добавлена переменная: ☁ {out}\n')
        else:
            self.add_text(f'Переменная ☁ {out} уже есть в списке переменных\n')

    def close_connection(self):
        self.ws.close()
        self.connection_menu.entryconfigure(0, state='disabled')
        self.connection_menu.entryconfigure(1, state='disabled')

    def enter_press(self, _):
        message = self.input_entry.get()
        full_message = f'{self.username}> {message}'
        try:
            self.ws.send_message(message)
            self.add_text(f'{full_message}\n')
            self.input_entry.delete(0, END)
        except cloud.WsClosedError:
            messagebox.Message(
                message=f'Соединение с проектом закрыто', 
                parent=win,
                icon=messagebox.ERROR,
            ).show()
        except NameError:
            length = len(full_message.encode(encoding=self.encoding))
            messagebox.Message(
                message=f'Слишком длинное сообщение!\nЗанято {length} из 79 байт в пакете', 
                parent=win,
                icon=messagebox.ERROR,
            ).show()
        except cloud.NoVarError:
            messagebox.Message(
                message=f'Список доступных облачных переменных пуст!\nДобавьте одно через меню "Соединение" или измените переменные через сам проект',
                parent=win,
                icon=messagebox.ERROR,
            ).show()
        except Exception as e:
            exc = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            print(exc)
            self.add_text(f'{exc}\n')

    def add_text(self, text: str):
        self.chat_text.configure(state='normal')
        self.chat_text.insert(END, text)

        self.chat_text.config(state='disabled')
        if self.autoscroll_value.get() == '1': self.chat_text.see(END)

    def recieve_text(self):
        while True:
            try:
                data = self.ws.recv()
                if data is None:
                    self.win.state()
                    continue

                self.add_text(data)
            except TclError:
                print('Tk window is dead, closing websocket...')
                if self.ws.ws is not None: self.ws.close()
                break
            except cloud.WsClosedError:
                self.add_text('Websocket connection closed\n')
                break
            except Exception as e:
                exc = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                print(exc)
                self.add_text(f'{exc}\n')
                if self.ws.ws is not None: self.ws.close()
                break

class LoginScreen:
    def __init__(self) -> None:
        ttk.Label(pad_frame, text='IESM клиент', font='bold').pack()

        self.form_frame = ttk.Labelframe(pad_frame, borderwidth=2, relief='groove', text='Вход')
        self.form_frame.pack()

        self.session_frame = ttk.Labelframe(self.form_frame, borderwidth=2, relief='ridge', text='Сессия')
        self.session_frame.pack(fill='y', side='left', padx=5)

        ttk.Label(self.session_frame, text="Имя пользователя:").pack(anchor='w')
        self.username_label = ttk.Entry(self.session_frame)
        self.username_label.pack()
        ttk.Label(self.session_frame, text="Пароль:").pack(anchor='w')
        self.password_label = ttk.Entry(self.session_frame, show='*')
        self.password_label.pack()

        self.address_frame = ttk.Labelframe(self.form_frame, borderwidth=2, relief='ridge', text='Адрес')
        self.address_frame.pack(fill='y', side='left', padx=5)

        ttk.Label(self.address_frame, text="ID Проекта:").pack(anchor='w')
        self.project_id_label = ttk.Entry(self.address_frame)
        self.project_id_label.pack()
        ttk.Label(self.address_frame, text="Имя комнаты:").pack(anchor='w')
        self.room_label = ttk.Entry(self.address_frame)
        self.room_label.pack()

        ttk.Label(self.form_frame, text='Кодировка:').pack(side='top', anchor='w')
        self.encoding_combo = ttk.Combobox(self.form_frame, values=(
            'ascii',
            'cp866',
            'cp1125',
            'cp1251',
            'latin_1',
            'iso8859_5',
            'koi8_r',
            'koi8_u',
            'utf_8',
        ), state='readonly')
        self.encoding_combo.set('iso8859_5')
        self.encoding_combo.pack(side='top')

        ttk.Label(self.form_frame, text='Тип соединения:').pack(side='top', anchor='w')
        self.connection_type = StringVar()
        self.connection_type.set('Scratch')
        ttk.Radiobutton(
            self.form_frame, 
            text='Scratch', value='Scratch', 
            variable=self.connection_type,
            command=self.set_password_state,
        ).pack(side='top', anchor='w')
        ttk.Radiobutton(
            self.form_frame, 
            text='Turbowarp', value='Turbowarp', 
            variable=self.connection_type,
            command=self.set_password_state,
        ).pack(side='top', anchor='w')

        ttk.Button(self.form_frame, text="Вход", command=self.chat_app).pack(side='bottom')

    def set_password_state(self):
        if self.connection_type.get() == 'Scratch':
            self.password_label.configure(state='normal')
        else:
            self.password_label.configure(state='disabled')

    def chat_app(self):
        global current_frame

        username = self.username_label.get().strip()
        password = self.password_label.get()
        room_name = self.room_label.get()
        encoding = self.encoding_combo.get()
        connection_type = self.connection_type.get()

        if username == '':
            messagebox.Message(
                message='Заполните все поля, чтобы продолжить', 
                parent=win,
                icon=messagebox.ERROR
            ).show()
            return

        if password == '' and connection_type == 'Scratch':
            messagebox.Message(
                message='Заполните все поля, чтобы продолжить', 
                parent=win,
                icon=messagebox.ERROR
            ).show()
            return

        try:
            project_id = int(self.project_id_label.get())
        except ValueError:
            messagebox.Message(
                message='Неверный ID проекта (Не является числом)', 
                parent=win,
                icon=messagebox.ERROR
            ).show()
            return

        ChatGUI(username, password, room_name, project_id, encoding, connection_type)

current_frame = LoginScreen()
win.mainloop()
