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
#    I've made it into an object oriented and use python's nice OptionParser
#    class
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

		class Record:
			pass

		# Load the options record with default values
		self.options = Record()
		self.options.targetsize = None
		self.options.login = None
		self.options.password = None
		self.options.targetalbum = None
		self.options.mode = 'upload'


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

		# Run
		if self.options.mode == 'list':
			self.listAlbums()
		else:
			# Upload the files
			for filename in self.filenames:
				self.upload( filename )

	#
	# Function:		authenticate
	# Description:
	#  Generate an authentication token to use for subsequent requests
	#
	def authenticate( self ):
#		try:
#			fauth = open('/tmp/googleauth', mode='r')
#			self.authtoken = fauth.read()
#			return
#		except IOError:
#			print "--- No cached authentication token found, new login"

		self.authtoken = None

		# Don't try to authenticate when no details supplied
		if not self.options.login or not self.options.password:
			return;

		# Create the authentication request
		auth_url = 'https://www.google.com/accounts/ClientLogin'
		auth_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
		auth_request = "Email=%s&Passwd=%s&service=lh2" % (self.options.login, self.options.password)

		if self.options.verbose:
			print "---- Authenticating"

		# Make the request
		response, content = self.http.request(auth_url, 'POST',
			body=auth_request, headers=auth_headers)

		if self.options.verbose:
			print "RX:",content
			print "RX:",response

		if response['status'] == '200':
			self.authtoken = re.search('Auth=(\S*)', content).group(1)

#		fauth = open('/tmp/googleauth', mode='w')
#		fauth.write(self.authtoken);
#		fauth.close()

	#
	# Function:		listAlbums
	# Description:
	#  Return a list of albums
	#
	def listAlbums( self ):
		if not self.options.login:
			raise TUPError("No username supplied, so can't list albums")

		url = 'http://picasaweb.google.com/data/feed/api/user/%s/?kind=album' % (self.options.login)

		if self.authtoken:
			headers = { 'Authorization': 'GoogleLogin auth=%s' % self.authtoken.strip() }
		else:
			headers = None

		if self.options.verbose:
			print "--- Listing albums for", self.options.login
		response, content = self.http.request(url, 'GET', headers=headers)
		if response['status'] == '404':
			raise TUPError(content)
		while response['status'] == '302':
			response, content = self.http.request(response['location'], 'GET')
			if response['status'] == '404':
				raise TUPError(content)

		for album in re.findall('<gphoto:name>(\S*)</gphoto:name>',content):
			print album

	#
	# Function:		upload
	# Description:
	#  Upload the given file
	#
	def upload( self, filename ):
		if not self.authtoken:
			raise TUPError("Not logged in while attempting upload")
		if not self.options.targetalbum:
			raise TUPError("You must supply an album name to upload to")

		if self.options.targetsize :
			tmpname = "/tmp/tmp%s" % (os.path.basename(filename))
			if self.options.verbose:
				print "--- Converting",filename,"to be",self.options.targetsize,"wide"
			os.system('convert -resize %s %s "%s"' % (self.options.targetsize,filename,tmpname))
			f = open((tmpname), mode='rb')
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
			self.createAlbum()
			response, content = self.http.request( url, 'POST',
				headers=headers,body=image )
			if response['status'] == '404':
				raise TUPError(content)

		# Check for a redirect
		while response['status'] == '302':
			response, content = self.http.request(response['location'], 'GET')
			if response['status'] == '404':
				raise TUPError(content)

		if self.options.verbose:
			print "RX:", content
			print "RX:", response

		if self.options.targetsize:
			os.system('rm -f "%s"' % (tmpname))

		print " - upload of", namenice, "complete"

	#
	# Function:		createAlbum
	# Description:
	#  Create the target album
	#
	def createAlbum( self ):
		if not self.authtoken:
			raise TUPError("Not logged in while attempting upload")
		if not self.options.targetalbum:
			raise TUPError("You must supply an album name to upload to")

		# URL to album
		url = 'http://picasaweb.google.com/data/feed/api/user/%s' % (self.options.login)
		summary = ""
		content = """
<entry xmlns='http://www.w3.org/2005/Atom'
xmlns:media='http://search.yahoo.com/mrss/'
xmlns:gphoto='http://schemas.google.com/photos/2007'>
<title type='text'>%s</title>
<summary type='text'>%s</summary>
<gphoto:access>public</gphoto:access>
<gphoto:commentingEnabled>true</gphoto:commentingEnabled>
<category scheme='http://schemas.google.com/g/2005#kind'
term='http://schemas.google.com/photos/2007#album'></category>
</entry>
""" % ( self.options.targetalbum, summary )
		headers = {
			'Authorization': 'GoogleLogin auth=%s' % self.authtoken.strip(),
			'Content-Length':'%s' % len(content),
			'Content-Type': 'application/atom+xml'
		}

		if self.options.verbose:
			print "--- Creating album", self.options.targetalbum
		response, content = self.http.request(url, 'POST', headers=headers, body=content)
		if response['status'] != '201':
			raise TUPError(content)

	#
	# Function:		readConfigFile
	# Description:
	#  Read default settings from config file
	#
	def readConfigFile( self ):
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
			usage="usage: %prog [options] [FILE] [FILE] [FILE]",
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
		parser.add_option( "", "--list", dest="mode",
			action="store_const", const="list",
			help="list albums")

		# Run the parser
		(self.options, args) = parser.parse_args( self.argv[1:] )

		if len(args) != 1 or self.options.mode == 'list':
			self.options.mode = 'list'

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

