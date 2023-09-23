#! /usr/bin/env python
# -*- coding: utf-8 -*-
# 2005-11-21 by Yüce TEKOL. http://www.geocities.com/yucetekol
# Last update: 2007-05-23

# DB Console
# Copyright (C) 2006, 2007  Yuce Tekol
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import os
import os.path
import getpass
from optparse import OptionParser

try:  # works on GNU
	import readline
except:
	pass

DEFAULT_ENCODING = "utf-8"

__VERSION__ = "0.6.7"

_PS1 = "[%(m)s]%(fn)s >>> "  # m: mode, fn: database name
_PS2 = "[%(m)s]%(fns)s ... "  # fns: # of spaces of length of the db name
MODE_SQLITE = "SQLite"
MODE_POSTGRES = "PostgreSQL"
MODE_MYSQL = "MySQL"
mode = MODE_SQLITE

# Are these safe?
HELP_FILENAME = os.path.join(os.environ["HOME"], ".dbcons/help.txt")
HISTORY_FILENAME = os.path.join(os.environ["HOME"], ".dbcons/history")

def print_columns(descs, rows):
	def print_nrows():
		nr = len(rows)
		if nr == 1:
			s = "row"
		else:
			s = "rows"
			
		print "(%d %s)" % (nr,s)

	collens = [len(d) for d in descs]
		
	for row in rows:
		for x, r in enumerate(row):
			collens[x] = max(collens[x], len(unicode(r)))
##			collens[x] = max(collens[x], len(r))
		
	format = "|"+(" %s |"*len(collens)) % \
		tuple(["%%%ds" % d for d in collens])
		
	header = format % tuple([d.center(c) for d,c in zip(descs, collens)])
	print "-"*len(header)
	print header
	print "-"*len(header)
	for row in rows:
		print format % row
	
	print "-"*len(header)	
	print_nrows()
			
def exec_sql(db, cmdstr, fetchone):
	# XXX: convert cmdstr to unicode
	cu = db.cursor()
	cu.execute(cmdstr)

	firstcmd = cmdstr.split(None,1)[0].lower()
	if firstcmd in ["select", "show"]:
		if fetchone:
			rows = [cu.fetchone()]
		else:
			rows = cu.fetchall()
			
		if cu.description:
			descs = [d[0].capitalize() for d in cu.description]
			print_columns(descs, rows)
		else:
			print "No rows"
			
	else:
		db.commit()

def set_prompt(filename):
	global PS1
	global PS2
	global mode

	filename = os.path.split(filename)[1]
	d = dict(fn=filename, fns=' '*len(filename), m=mode[0])
	PS1 = _PS1 % d
	PS2 = _PS2 % d

	return PS1

def main():
	global mode
	
	default_user = getpass.getuser()
	opt = OptionParser(usage="usage: %prog [options] database_name",
			version="dbconsole %s" % __VERSION__)
	opt.add_option("-s", "--sql", dest="sqlcmd",
			help="Execute an sql command and exit")
	opt.add_option("-n", "--noninteractive", action="store_true",
			help="Enter non-interactive mode")
	opt.add_option("-1", "--fetchone", action="store_true",
			help="Return only one row.")
	opt.add_option("-m", "--mode", choices=["sqlite", "postgresql", "mysql", "s", "p", "m"],
			help="Select an operation mode: sqlite, postgresql or mysql; you can use the initial letters")
	opt.add_option("-H", "--host")
	opt.add_option("-P", "--port")
	opt.add_option("-u", "--user", default=default_user,
			help="The username to connect to the database, default: %s" % default_user)
	opt.add_option("-p", "--password")
	opt.add_option("--ask-pass", dest="askpass", action="store_true",
			help="Enter the password interactively")
	
	options, args = opt.parse_args()

	if options.askpass:
		passw = getpass.getpass()
	else:
		passw = options.password
		
	dbname = args and args[0] or ""

	if not args or options.mode in [None, "sqlite", "s"]:  # XXX: if not args, we should err.
		try:
			from pysqlite2 import dbapi2 as sql
		except ImportError:
			# No seperate pysqlite2, maybe we're on Python 2.5+
			try:
				import sqlite3 as sql
			except ImportError:
				# Nope!
				print "You don't have pysqlite2, please install it in order to use SQLite mode"
				sys.exit(1)
		
		mode = MODE_SQLITE
		
		if args:
			db = sql.connect(dbname)
			filename = dbname
		else:
			filename = "No DB"
			db = None
			
	elif options.mode in ["p", "postgresql"]:
		try:
			import psycopg as sql
		except ImportError:
			print "You don't have psycopg, please install it in order to use PostgreSQL mode"
			sys.exit(1)			
		
		dsn = " ".join([options.host and ("host=%s" % options.host) or "",
				options.port and ("port=%s" % options.port) or "",
				dbname and ("dbname=%s" % dbname) or "",
				options.user and ("user=%s" % options.user) or "",
				passw and ("password=%s" % passw) or ""])
				
		db = sql.connect(dsn)
		filename = dbname
		mode = MODE_POSTGRES

	elif options.mode in ["m", "mysql"]:
		dsn = dict([x for x in ("host",options.host or None),
				("port",options.port or None),
				("db",dbname or None),
				("user",options.user or None),
				("passwd",passw or None) if x[1]])

		try:
			import MySQLdb as sql
		except ImportError:
			print "You don't have MySQLdb, please install it in order to use MySQL mode"
			sys.exit(1)
			
		db = sql.connect(**dsn)
		filename = dbname
		mode = MODE_MYSQL
		
	if options.sqlcmd:
		if not args:
			print>>sys.stderr, "error: DB file not specified!"
			sys.exit(10)

		try:
			try:
				exec_sql(db, options.sqlcmd, options.fetchone)
			except sql.DatabaseError, e:
				print>>sys.stderr, e
				sys.exit(10)
		finally:
			db.close()

		sys.exit()

	if not options.noninteractive:
		print "DB Console %s: %s" % (__VERSION__,filename)
		print "Type '\quit' to exit,"
		print "     '\help' for help\n"
		
		print "Mode:", mode
		# Try to load the help file
		try:
			helpf = file(HELP_FILENAME)
			help = eval(helpf.read())
			helpf.close()
		except IOError:
			print "Help file not loaded"  ###
			help = {}
			
		help["help"] = "Try \help intro"  # TODO: change this!!!
		
		# Try to load the command histoy
		try:
			readline.read_history_file(HISTORY_FILENAME)
		except:
			pass

	cmdstr = ""
	prompt = set_prompt(filename)
	while True:
		try:
			try:
				if options.noninteractive:
					cmdin = raw_input().strip()
				else:
					cmdin = raw_input(prompt).strip()					
			except KeyboardInterrupt:
				if cmdstr:
					print
					prompt = PS1
					cmdstr = ""
				else:
					print
					
				continue	
				
			cmdin = cmdin.strip()
			
			if not cmdin:
				continue				
			if not ";" in cmdin:
				if not cmdstr:
					cmd = cmdin.lower()
					if cmd in [r"\quit", r"\q"]:
						break
					elif cmd.startswith(r"\open") or cmd.startswith(r"\o"):
						filename = cmd.split()[1]
						prompt = set_prompt(filename)
						db = sql.connect(filename)						
					elif cmd.startswith(r"\help") or cmd.startswith(r"\h"):
						items = cmd.split()
						if len(items) == 1:
							print help.get("help", "No help")
						else:
							print help.get(" ".join(items[1:]), "No help")
					elif cmd == r"\tables":
						if mode == MODE_SQLITE:
							exec_sql(db, "select name from sqlite_master where type='table' order by name;", False)
						elif mode == MODE_MYSQL:
							exec_sql(db, "show tables;", False)
						elif mode == MODE_POSTGRES:
							# filter tables with names starting with pg_ or sql_
							exec_sql(db, """select relname from pg_class where
							relkind='r' and not relname like 'pg_%'
							and not relname like 'sql_%' order by relname;""", False)
					else:
						cmdstr += cmdin + "\n"
						prompt = PS2
				else:
					cmdstr += cmdin + "\n"

				continue

			else:
				cmdstr += cmdin
				prompt = PS1
				
				for cmd in cmdstr.split(";"):
					cmd = cmd.strip()
					if not cmd:
						continue		
					if not db:
						print>>sys.stderr, "error: DB not open. Use '\open' command."
					else:
						exec_sql(db, cmd, options.fetchone)
						
			cmdstr = ""

		except EOFError:
			break		
		except sql.DatabaseError, e:
			print e
			cmdstr = ""

	if db:
		db.close()
		
	try:  # to save the command history
		readline.write_history_file(HISTORY_FILENAME)
	except:
		pass

	if not options.noninteractive:
		print "\nBye!"

if __name__ == "__main__":
	main()

