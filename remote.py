# remote.py: Cornice remote control
# arch-tag: Cornice remote control
# author: Alberto Griggio <agriggio@users.sourceforge.net>
# license: GPL

import os, sys, stat
import socket, select
import threading


if os.name == 'posix':
    socket_addr = '/tmp/cornice%s' % os.getuid()
else:
    socket_addr = ('127.0.0.1', 19580)


def get_server_socket():
    if os.name == 'posix':
        family = socket.AF_UNIX
        if os.path.exists(socket_addr):
            try:
                os.unlink(socket_addr)
            except OSError as e:
                raise socket.error(str(e))
    else:
        family = socket.AF_INET
    s = socket.socket(family, socket.SOCK_STREAM)
    s.bind(socket_addr)
    return s


def get_client_socket():
    if os.name == 'posix':
        if not os.path.exists(socket_addr):
            return None
        info = os.lstat(socket_addr)
        if not stat.S_ISSOCK(info.st_mode):
            return None
        family = socket.AF_UNIX
    else:
        family = socket.AF_INET
    s = socket.socket(family, socket.SOCK_STREAM)
    s.connect(socket_addr)
    return s


def ping():
    retval = False
    try:
        s = get_client_socket()
        if s is None:
            return False
        f = s.makefile()
        f.write('PING:\n')
        f.flush()
        print('sent PING')
        if f.readline() == '0\n':
            print('OK!')
            retval = True
        s.close()
    except socket.error:
        #import traceback; traceback.print_exc()
        retval = False
    return retval
      

def do_command(cmd, *args):
    """\
    Executes the command `cmd' remotely. Returns the exit status.
    """
    try:
        sock = get_client_socket()
        if sock is None:
            return 1
        f = sock.makefile()
        args = [a.replace('\n', '') for a in args]
        f.write('%s: %s\n' % (cmd, " ".join(args)))
        f.flush()
        status = int(f.readline())
        sock.close()
        return status
    except (socket.error, IOError) as errno:#(errno, strerr):
        return errno


def init_server(app):
    me = sys.modules[__name__]
    import wx
    setattr(me, 'wx', wx)

    _EVT_REMOTE_COMMAND = wx.NewEventType()

    class RemoteCommandEvent(wx.PyCommandEvent):
        def __init__(self, cmd, args):
            wx.PyCommandEvent.__init__(self)
            self.SetEventType(_EVT_REMOTE_COMMAND)
            self.cmd = cmd
            self.args = args

    # end of class RemoteCommandEvent
    setattr(me, 'RemoteCommandEvent', RemoteCommandEvent)

    if wx.VERSION[:2] >= (2, 5):
        EVT_REMOTE_COMMAND = wx.PyEventBinder(_EVT_REMOTE_COMMAND, 0)
    else:
        def EVT_REMOTE_COMMAND(win, function):
            win.Connect(-1, -1, _EVT_REMOTE_COMMAND, function)
    setattr(me, 'EVT_REMOTE_COMMAND', EVT_REMOTE_COMMAND)

    t = _RemoteConnectionListener(app)
    t.setDaemon(True)
    return t


def shutdown_server():
    if os.name == 'posix':
        try:
            os.unlink(socket_addr)
        except Exception as e:
            print(e)


class _RemoteConnectionListener(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.app = app
        try:
            self.sock = get_server_socket()
        except socket.error:
            self.sock = None

    def run(self):
        if self.sock is None:
            return
        self.sock.listen(1)
        import common
        while not common.exiting():
            conn, addr = self.sock.accept()
            # ALB 2004-12-27: accept connections from localhost only...
            if os.name != 'posix' and addr[0] != '127.0.0.1':
                conn.close()
                continue
            try:
                f = conn.makefile()
                bits = []
                cmd, args = f.readline().strip().split(':', 1)
                print('received:', cmd, args)
                wx.PostEvent(self.app, RemoteCommandEvent(cmd, args.split()))
                f.write('0\n')
                f.flush()
                conn.close()
            except Exception as e:
                import traceback
                traceback.print_exc()

# end of class _RemoteConnectionListener
