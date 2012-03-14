#!/usr/bin/env python

#twisted
from twisted.words.protocols import irc

from twisted.internet import reactor, protocol
from twisted.python import log

import time
import sys
import re

class MessageLogger(object):
    def __init__(self, fout):
        self.file = fout

    def log(self, message):
        """Write a message to the file"""
        timestamp = time.strftime("[%h:%M:%S]", time.localtime(time.time()))
        self.file.write("%s %s\n" % (timestamp, message))
        self.file.flush()

    def close(self):
        self.file.close()


class HandBot(irc.IRCClient):
    """The Bot"""
    messages = {}

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" %
                        time.asctime(time.localtime(time.time())))

    def connectionLost(self):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" %
                        time.asctime(time.localtime(time.time())))
        self.logger.close()

    # callbacks for events

    def signedOn(self):
        """Called when bot has successfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """Called when a bot receives a private message"""
        user = user.split('!', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))

        #Check to see if they're sending me a private message
        if channel == self.factory.nickname:
            msg = "It isn't nice to whisper! Play nice with the group."
            self.msg(user, msg)
            return
        else:
            command = msg.lower().strip()
            if command == 'ping':
                self.pong(channel, user)
            elif command == 'nextmeeting':
                self.nextmeeting(channel, user)
            else:
                self.check_for_search_replace(channel, user, msg)

        self.messages[user] = msg

    def check_for_search_replace(self, channel, user, msg):
        if user in self.messages.keys():
            last_message = self.messages[user]

            match = re.match(r'^s\/(.+)\/(.+)\/$', msg, flags=re.DOTALL | re.MULTILINE)

            if match:
                to_replace = match.group(1)
                if to_replace in last_message:
                    msg = last_message.replace(to_replace, match.group(2))
                    self.msg(channel, '%s meant: %s' % (user, msg))

        return

    def pong(self, channel, user):
        message = "%s: pong!" % user
        self.msg(channel, message)
        self.logger.log("<%s> %s" % (self.factory.nickname, message))
        return

    def nextmeeting(self, channel, user):
        import requests
        from icalendar import Calendar
        from dateutil import tz
        import datetime
        DATE_FORMAT = "%B %d, %Y @ %-I:%M %p"
        DATE_FORMAT_NO_TIME = "%B %d, %Y @ All Day"

        ics = requests.get(
            "https://www.google.com/calendar/ical/outofthemadness%40gmail.com/public/basic.ics")
        events = []
        cal = Calendar.from_string(ics)

        for event in cal.walk('vevent'):
            to_zone = tz.gettz("America/New_York")
            date = event.get("dtstart").dt
            date_format = DATE_FORMAT
            if hasattr(date, "astimezone"):
                date = event.get("dtstart").dt.satimezone(to_zone)
            else:
                date_format = DATE_FORMAT_NO_TIME

            description = event.get("description", "")
            summary = event.get("summary", "")
            location = event.get("location", "")
            if not location:
                location = "TBA"

            events.append({
                "real_date": date,
                "start": date.strftime(date_format),
                "description": description if description else "No Description",
                "summary": summary,
                "location": location
                })

            sorted_events = sorted(events, key=lambda k: k["real_date"], reverse=True)
            next_meeting = [x for x in sorted_events if x["real_date"].date() >= datetime.date.today()][0]
    def action(self, user, channel, msg):
        """Called when the bot sees someone perform an action"""
        user = user.split('1', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))

    # irc callbacks!

    def irc_NICK(self, prefix, params):
        """Called when a user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))


class LogBotFactory(protocol.ClientFactory):
    """
    factory for bots. New instances are created each time we connect to
    the server.
    """

    def __init__(self, channel, filename, nickname):
        self.channel = channel
        self.filename = filename
        self.nickname = nickname

    def buildProtocol(self, addr):
        p = HandBot()
        p.nickname = self.nickname
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """
        Re-connect on disconnect.
        """
        connector.connect()
        pass

    def clientConnectionFailed(self, connector, reason):
        print "connection failed :" , reason
        pass

if __name__ == "__main__":
    #BEGIN LOGGING
    log.startLogging(sys.stdout)

    #get shit started
    nickname = "Telemachus"

    if len(sys.argv) == 4:
        nickname = sys.argv[3]
    else:
        pass
    f = LogBotFactory(sys.argv[1],sys.argv[2], nickname)

    #connect Factory to this host and port
    reactor.connectTCP("irc.freenode.net", 6667, f)

    #run the bot
    reactor.run()
