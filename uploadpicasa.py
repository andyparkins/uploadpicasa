#!/usr/bin/python
# ----------------------------------------------------------------------------
# Project: uploadpicasa
#
# Version Control
#    $Author$
#      $Date$
#        $Id$
#
# Legal
#    Copyright 2007  Andrea Rizzi, Andy Parkins
#
# Notes
#    Adapted from snippet posted by Andrea on the dot.kde.org thread at
#    http://dot.kde.org/1181138874/
#    I've made it into an object oriented and use python's nice OptionParser class
#
# ----------------------------------------------------------------------------

# ----- Includes

# Standard library
import httplib2, re
import sys
import os
import locale

from optparse import OptionParser


# ----- Constants


# ----- Class definitions

#
# Class:
# Description:
#
class TUPError(Exception):
	pass

#
# Class:	TUploadPicasa
# Description:
#
class TUploadPicasa:
	#
	# Function:		__init__
	# Description:
	#
	def __init__( self, argv ):
		self.argv = argv

	#
	# Function:		run
	# Description:
	#  Main function, read config, read command line, authenticate
	#  and upload
	#
	def run( self ):
		self.readConfigFile()
		self.readCommandLine()

		if self.options.verbose:
			print "--- Verbose mode object dump"
			print self

		# Create a httplib object for doing the web work
		self.http = httplib2.Http()
		# Establish authtoken
		self.authenticate()

		if not self.authtoken:
			raise TUPError("Couldn't log in")

		# Upload the files
		for filename in self.filenames:
			self.upload( filename )

	#
	# Function:		authenticate
	# Description:
	#  Generate an authentication token to use for subsequent requests
	#
	def authenticate( self ):
		try:
			fauth = open('/tmp/googleauth', mode='r')
			self.authtoken = fauth.read()
			return
		except IOError:
			print "--- No cached authentication token found, new login"

		# Create the authentication request
		auth_url = 'https://www.google.com/accounts/ClientLogin'
		auth_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
		auth_request = "Email=%s&Passwd=%s&service=lh2" % (self.options.login, self.options.password)

		# Make the request
		response, content = self.http.request(auth_url, 'POST',
			body=auth_request, headers=auth_headers)

		print response
		print content

		if response['status'] == '200':
			self.authtoken = re.search('Auth=(\S*)', content).group(1)
		else:
			self.authtoken = None

		fauth = open('/tmp/googleauth', mode='w')
		fauth.write(self.authtoken);
		fauth.close()

	#
	# Function:		upload
	# Description:
	#  Upload the given file
	#
	def upload( self, filename ):
		if self.options.targetsize :
			if self.options.verbose:
				print "--- Converting",filename,"to be",self.options.targetsize,"wide"
			os.system('convert -resize %s %s /tmp/tmp.jpg' % (self.options.targetsize,filename))
			f = open('/tmp/tmp.jpg', mode='rb')
		else :
			f = open(filename, mode='rb')

		# Strip the path part from the filename for display
		namenice = re.sub(".*/", "", filename)

		# URL to album
		url = 'http://picasaweb.google.com/data/feed/api/user/%s/album/%s' % (self.options.login,self.options.targetalbum)
		comment = ""
		header = """Media multipart posting
--END_OF_PART
Content-Type: application/atom+xml

<entry xmlns='http://www.w3.org/2005/Atom'>
  <title>%s</title>
  <summary>%s</summary>
  <category scheme="http://schemas.google.com/g/2005#kind"
    term="http://schemas.google.com/photos/2007#photo"/>
</entry>
--END_OF_PART
Content-Type: image/jpeg

""" % (namenice,comment)
		footer = "\n--END_OF_PART--"

		# Wrap the image and find its size
		image = header + f.read() + footer;
		fsize = len(image)

#		headers = {'Content-Type':'image/jpeg','Content-Length': '%s' % fsize,
#			'Slug':'%s' % filename,
#			'Authorization': 'GoogleLogin auth=%s' % self.authtoken.strip()}

		print "Uploading image", namenice, "size", fsize

		headers = { 'Authorization': 'GoogleLogin auth=%s' % self.authtoken.strip(),
			'Content-Type':'multipart/related; boundary=END_OF_PART',
			'Content-Length':'%s' % fsize,
			'MIME-versio':'1.0' }

		if self.options.verbose:
			print "----- Transmitting to album"
			print "TX:", headers

		response, content = self.http.request( url, 'POST',
			headers=headers,body=image )
		if response['status'] == '404':
			raise TUPError(content)
		if self.options.verbose:
			print "RX:", content
			print "RX:", response

		if self.options.verbose:
			print "----- Fetching response"
		while response['status'] == '302':
			response, content = http.request(response['location'], 'GET')

		if self.options.verbose:
			print "RX:", content
			print "RX:", response

		if self.options.targetsize:
			os.system('rm /tmp/tmp.jpg')

		print " - upload of", namenice, "complete"

	#
	# Function:		readConfigFile
	# Description:
	#  Read default settings from config file
	#
	def readConfigFile( self ):
		class Record:
			pass

		# Load the options record with default values
		self.options = Record()
		self.options.targetsize = None
		self.options.login = None
		self.options.password = None
		self.options.targetalbum = None

		# Read overriding defaults from the config file
		home = os.getenv('HOME');
		try:
			fconfig = open(home+'/.uploadpicasarc', mode='r')
		except IOError:
			return

		config = fconfig.read();

		config = config.split("\n");

		for line in config:
			if len(line) == 0:
				continue
			splitline = line.split('=')
			param = splitline[0].strip()
			value = ".".join(splitline[1:]).strip()
			if param == 'login':
				self.options.login = value
			elif param == 'password':
				self.options.password = value
			elif param == 'targetwidth':
				self.options.targetsize = value
			elif param == 'album':
				self.options.targetalbum = value

	#
	# Function:		readCommandLine
	# Description:
	#  Parse the command line with OptionParser; which supplies all the
	#  niceties for us (like --help, --version and validating the inputs)
	#
	def readCommandLine( self ):
#		opts, args = getopt.getopt(sys.argv[1:], "hr:a:v", ["help", "resize=","album="])

		# Configure parser
		parser = OptionParser(
			usage="usage: %prog [options] FILE [FILE] [FILE]",
			version="%prog 1.0")
		# "-h", "--help" supplied automatically by OptionParser
		parser.add_option( "-v", "--verbose", dest="verbose",
			action="store_true",
			help="show verbose output")
		parser.add_option( "-l", "--login", dest="login",
			metavar="USERNAME", type='string', default=self.options.login,
			help="the username of your google picasaweb account [default:%default]")
		parser.add_option( "-p", "--password", dest="password",
			metavar="PASSWORD", type='string', default=self.options.password,
			help="the password of your google picasaweb account [default:NOT SHOWN]")
		parser.add_option( "-r", "--resize", dest="targetsize",
			metavar="WIDTH", type='int', default=self.options.targetsize,
			help="the width the image should be in picasa [default:%default]")
		parser.add_option( "-a", "--album", dest="targetalbum",
			metavar="ALBUM", type='string', default=self.options.targetalbum,
			help="the destination picasa album [default:%default]")

		# Run the parser
		(self.options, args) = parser.parse_args( self.argv[1:] )

		# Ensure that we have the parameters we need
		if len(args) != 1:
			parser.error("You must supply the name of a FILE to upload")

		if not self.options.targetalbum:
			parser.error("You must supply the name of an ALBUM to upload to")

		if not self.options.login or not self.options.targetalbum:
			parser.error("You must supply a USERNAME and PASSWORD to login")

		# Copy the positional arguments into self
		self.filenames = args

	#
	# Function:		__str__
	# Description:
	#  Dump the contents of this class to a string
	#
	def __str__( self ) :
		s = repr(self) + "\n";
		for var in self.__dict__ :
			s = s + " - " + var + " = " + str(self.__dict__[var]) + "\n"
		return s


# ----- Main
#
# Function:		main
# Description:
#
def main( argv = None ):
	# Default arguments from command line
	if argv is None:
		argv = sys.argv

	# Locale
	locale.setlocale( locale.LC_ALL, '' );

	app = TUploadPicasa( argv )

	# --- Begin
	try:
		app.run()

	# Simply display TUPErrors
	except TUPError, e:
		print "ERROR:",e.args[0]


# ----- Module check
#
# __name__ is set to "__main__" when this is the top module
# if this module is loaded because of an "import" then this
# won't get run -- perfect
if __name__ == "__main__":
	sys.exit( main() )

