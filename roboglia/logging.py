
class Logger():

    class __Logger():

        def __init__(self, logFile, color):
            if logFile == '':
                self.logFile = None
            else:
                self.logFile = open(logFile, 'a+')
            self.RED = '\033[31m' if color else ''
            self.GREEN = '\033[32m' if color else ''
            self.YELLOW = '\033[33m' if color else ''
            self.BLUE = '\033[34m' if color else ''
            self.MAGENTA = '\033[35m' if color else ''
            self.RESET = '\033[39m' if color else ''

            self.debugFunc = self.showNone
            self.infoFunc = self.showNone
            self.warnFunc = self.defaultWarnFunc
            self.errFunc = self.defaultErrFunc
            self.fatalFunc = self.defaultFatalFunc

        def showCommon(self, msg):
            print(msg)
            if self.logFile != None:
                self.logFile.write(msg + '\n')

        def showNone(self, msg):
            if self.logFile != None:
                self.logFile.write(msg + '\n')

        def defaultDebugFunc(self, msg):
            self.showCommon(self.BLUE + '[DEBUG]: ' + self.RESET + msg)

        def defaultInfoFunc(self, msg): 
            self.showCommon('[INFO]: ' + msg)

        def defaultWarnFunc(self, msg): 
            self.showCommon(self.YELLOW + '[WARN]: ' + self.RESET + msg)

        def defaultErrFunc(self, msg):
            self.showCommon(self.RED + '[ERROR]: ' + self.RESET + msg)

        def defaultFatalFunc(self, msg):
            self.showCommon(self.MAGENTA + '[FATAL]: ' + self.RESET + msg)

        def DEBUG(self, msg):
            self.debugFunc(msg)

        def INFO(self, msg):
            self.infoFunc(msg)

        def WARN(self, msg):
            self.warnFunc(msg)

        def ERR(self, msg):
            self.errFunc(msg)

        def FATAL(self, msg):
            self.fatalFunc(msg)

    instance = None

    def __init__(self, logFile='', color=True):
        if not Logger.instance:
            Logger.instance = Logger.__Logger(logFile, color)

    def __getattr__(self, attr):
        return getattr(self.instance, attr)

    def __setattr__(self, attr, value):
        return setattr(self.instance, attr, value)
