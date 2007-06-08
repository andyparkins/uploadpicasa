#!/usr/bin/python
import httplib2, re
import sys
import os
import getopt


def usage():
   print "no documentation"

login = ''
password = ''
#url = 'http://picasaweb.google.com/data/feed/api/user/%s/album/Varie?kind=photo' % login
try:
    opts, args = getopt.getopt(sys.argv[1:], "hr:a:v", ["help", "resize=","album="])
except getopt.GetoptError:
    # print help information and exit:
    usage()
    sys.exit(2)

rsize = None
album = None
for o, a in opts:
     if o == "-v":
         verbose = True
     if o in ("-h", "--help"):
         usage()
         sys.exit()
     if o in ("-r", "--resize"):
         rsize = a
     if o in ("-a", "--album"):
         album = a

if not album:
	foptions = open("/home/bilibao/.picasaupload",mode="r")
        album = foptions.read()

url = 'http://picasaweb.google.com/data/feed/api/user/%s/album/%s' % (login,album)
print url
print  rsize 
print  album
def authenticate(http):
    auth_url = 'https://www.google.com/accounts/ClientLogin'
    auth_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    auth_request = "Email=%s&Passwd=%s&service=lh2" % (login, password)  
    response, content = http.request(auth_url, 'POST', body=auth_request, headers=auth_headers) 
    print response
    print content
    if response['status'] == '200':
        return re.search('Auth=(\S*)', content).group(1)
    else:
        return None

http = httplib2.Http()  
try:
    fauth = open('/tmp/googleauth', mode='r')
    auth = fauth.read()
except IOError:
        print "New login"
   	auth = authenticate(http)  
        fauth = open('/tmp/googleauth', mode='w')
        fauth.write(auth);
        fauth.close()        




def upload(name,size):
        if size :
        	os.system('convert -resize %s %s /tmp/tmp.jpg' %(size,name))
	        f = open('/tmp/tmp.jpg', mode='rb')
        else :
                f = open(name,mode='rb')

        namenice = re.sub(".*/", "", name)
        print namenice 
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
        image = header + f.read() + footer;
        
	fsize = len(image)
        headers = {'Content-Type':'image/jpeg','Content-Length': '%s' % fsize,'Slug':'%s'%name, 'Authorization': 'GoogleLogin auth=%s' % auth.strip()}
        body = image
        print fsize
        headers =  { 'Authorization': 'GoogleLogin auth=%s' % auth.strip(), 'Content-Type':'multipart/related; boundary=END_OF_PART',
	'Content-Length':'%s'% fsize,'MIME-versio':'1.0' } 
	print headers
        response, content = http.request(url, 'POST', headers=headers,body=body)

        print content
        print response
        while response['status'] == '302':
                response, content = http.request(response['location'], 'GET')
        print content
        print response
 
        os.system('rm /tmp/tmp.jpg')

if auth:
    for image in args :
      upload(image,rsize)        
else:
    print "Unable to Login"
 
